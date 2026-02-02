"""
Executor Agent (Vibium)
Responsible for executing test steps using Vibium browser automation
"""

import asyncio
import socket
import os
from models import TestStep, ExecutionResult
from ollama_client import OllamaClient


class VibiumExecutorAgent:
    """Agent responsible for executing test steps using Vibium"""
    
    def __init__(self, llm_client: OllamaClient, headless: bool = False):
        self.llm = llm_client
        self.browser = None
        self.page = None
        self.headless = headless
        self.wait_timeout = 10000  # milliseconds
        
    async def initialize_browser(self):
        """Initialize the Vibium browser"""
        try:
            # Try multiple import styles to support different vibium versions
            VibiumBrowser = None
            try:
                from vibium import Browser as VibiumBrowser
            except Exception as e1:
                try:
                    from vibium import browser as VibiumBrowser
                except Exception as e2:
                    try:
                        import vibium as _vib
                        VibiumBrowser = getattr(_vib, 'Browser', None) or getattr(_vib, 'browser', None)
                        if VibiumBrowser is None:
                            raise ImportError("Could not find 'Browser' or 'browser' in vibium package")
                    except Exception as e3:
                        raise ImportError(f"Failed to import vibium: {e1}, {e2}, {e3}")

            if VibiumBrowser is None:
                raise ImportError("Could not find vibium Browser class")

            # Instantiate browser with fallback options
            try:
                if callable(VibiumBrowser):
                    try:
                        self.browser = VibiumBrowser(headless=self.headless)
                    except TypeError:
                        self.browser = VibiumBrowser()
                else:
                    class_candidate = getattr(VibiumBrowser, 'Browser', None)
                    if class_candidate:
                        try:
                            self.browser = class_candidate(headless=self.headless)
                        except TypeError:
                            self.browser = class_candidate()
                    else:
                        raise ImportError("vibium browser interface not compatible")
            except Exception as e:
                print(f"[DEBUG] Browser instantiation error: {e}")
                raise

            # Launch browser with port handling
            await self._launch_browser()

            # Start the browser
            await self._start_browser()

            # Create a new page
            await self._create_page()

            print("✓ Vibium browser initialized")

        except ImportError as ie:
            print(f"ERROR: Vibium not installed or incompatible. Install with: pip install vibium")
            print(f"[DEBUG] Import error: {ie}")
            raise
        except Exception as e:
            print(f"ERROR initializing Vibium: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _launch_browser(self):
        """Launch browser with port handling"""
        # Check if launch method exists
        if not hasattr(self.browser, 'launch'):
            print("[DEBUG] Browser has no 'launch' method, skipping launch")
            return
        
        launch = getattr(self.browser, 'launch')
        if not callable(launch):
            print("[DEBUG] Browser.launch is not callable, skipping")
            return

        launched = None

        def _find_free_port() -> int:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            port = s.getsockname()[1]
            s.close()
            return port

        ports_to_try = [_find_free_port() for _ in range(5)]

        # Find Chrome executable on Windows
        chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', "C:\\Program Files"), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', "C:\\Program Files (x86)"), 'Google', 'Chrome', 'Application', 'chrome.exe')
        ]
        executable_path = None
        for p in chrome_paths:
            if p and os.path.exists(p):
                executable_path = p
                break

        last_error = None
        for port in ports_to_try:
            try:
                kwargs = {'port': port}
                if executable_path:
                    kwargs['executable_path'] = executable_path

                if asyncio.iscoroutinefunction(launch):
                    try:
                        launched = await launch(headless=self.headless, **kwargs)
                    except TypeError:
                        launched = await launch(**kwargs)
                else:
                    try:
                        launched = launch(headless=self.headless, **kwargs)
                    except TypeError:
                        launched = launch(**kwargs)

                if launched:
                    print(f"✓ Browser launched (port {port})")
                    break
            except Exception as e:
                last_error = e
                print(f"[DEBUG] Port {port} failed: {e}")
                await asyncio.sleep(0.2)

        if launched:
            self.browser = launched
        else:
            # If launch failed, the browser object might still be usable
            print(f"[DEBUG] All launch attempts failed. Last error: {last_error}. Continuing with browser object as-is.")

    async def _start_browser(self):
        """Start the browser if needed"""
        start = getattr(self.browser, 'start', None)
        if start:
            if asyncio.iscoroutinefunction(start):
                await self.browser.start()
            elif callable(start):
                self.browser.start()

    async def _create_page(self):
        """Create a new page"""
        try:
            if hasattr(self.browser, 'new_page'):
                new_page = getattr(self.browser, 'new_page')
                if asyncio.iscoroutinefunction(new_page):
                    self.page = await new_page()
                else:
                    self.page = new_page()
            elif hasattr(self.browser, 'newPage'):
                np = getattr(self.browser, 'newPage')
                if asyncio.iscoroutinefunction(np):
                    self.page = await np()
                else:
                    self.page = np()
            elif hasattr(self.browser, 'page'):
                self.page = getattr(self.browser, 'page')
            elif hasattr(self.browser, 'goto') or hasattr(self.browser, 'go'):
                # Browser itself can be used as a page
                self.page = self.browser
            else:
                # Try to use browser as page if it has basic navigation methods
                print("[DEBUG] Could not find standard page creation method, using browser as page")
                self.page = self.browser
        except Exception as e:
            print(f"[DEBUG] Page creation failed: {e}. Attempting to use browser as page.")
            if hasattr(self.browser, 'goto') or hasattr(self.browser, 'go'):
                self.page = self.browser
            else:
                raise Exception("Could not create a new page from vibium browser")
    
    async def close_browser(self):
        """Close the browser"""
        if self.browser:
            try:
                closed = False
                for name in ('close', 'stop', 'shutdown'):
                    method = getattr(self.browser, name, None)
                    if method:
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                        closed = True
                        break

                self.browser = None
                self.page = None
            except Exception as e:
                print(f"Error closing browser: {e}")
    
    async def execute_step(self, step: TestStep) -> ExecutionResult:
        """Execute a single test step"""
        if not self.browser:
            await self.initialize_browser()
        
        try:
            if step.action == "navigate":
                return await self._execute_navigate(step)
            elif step.action == "click":
                return await self._execute_click(step)
            elif step.action == "type":
                return await self._execute_type(step)
            elif step.action == "verify":
                return await self._execute_verify(step)
            elif step.action == "wait":
                return await self._execute_wait(step)
            elif step.action == "scroll":
                return await self._execute_scroll(step)
            else:
                return ExecutionResult(
                    step_number=step.step_number,
                    action=step.action,
                    success=False,
                    message=f"Unknown action: {step.action}"
                )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Error executing step: {str(e)}"
            )
    
    async def _execute_navigate(self, step: TestStep) -> ExecutionResult:
        """Navigate to a URL"""
        url = step.target if step.target.startswith('http') else f"https://{step.target}"
        
        try:
            # Try different navigation methods
            if hasattr(self.page, 'goto'):
                await self.page.goto(url, timeout=30000)
            elif hasattr(self.page, 'go'):
                go_method = getattr(self.page, 'go')
                if asyncio.iscoroutinefunction(go_method):
                    await go_method(url)
                else:
                    go_method(url)
            elif hasattr(self.page, 'navigate'):
                navigate_method = getattr(self.page, 'navigate')
                if asyncio.iscoroutinefunction(navigate_method):
                    await navigate_method(url)
                else:
                    navigate_method(url)
            else:
                raise Exception(f"No navigation method found (goto, go, or navigate). Available methods: {dir(self.page)}")
            
            await asyncio.sleep(2)
            
            # Determine actual result (prefer page URL or title when available)
            actual = None
            if hasattr(self.page, 'url'):
                actual = getattr(self.page, 'url')
            elif hasattr(self.page, 'current_url'):
                actual = getattr(self.page, 'current_url')
            else:
                actual = url

            # If planner provided an expected_result, evaluate it briefly
            success = True
            message = f"Navigated to {url}"
            if step.expected_result:
                # If expected_result looks like a URL, compare URL, otherwise check page content
                try:
                    if step.expected_result.startswith('http'):
                        success = step.expected_result.rstrip('/') == (actual or '').rstrip('/')
                        if not success:
                            message = f"Navigated to {url} (expected {step.expected_result}, got {actual})"
                    else:
                        page_text = None
                        if hasattr(self.page, 'content'):
                            page_text = await self.page.content()
                        elif hasattr(self.page, 'evaluate'):
                            page_text = await self.page.evaluate('document.body.innerText')

                        if page_text and step.expected_result.lower() not in page_text.lower():
                            success = False
                            message = f"Expected content '{step.expected_result}' not found after navigation"
                except Exception:
                    # Don't fail navigation if post-check errors; report as non-critical
                    success = False

            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=success,
                message=message,
                actual_result=actual
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Navigation failed: {str(e)}"
            )
    
    async def _find_element(self, target: str):
        """Find element using Vibium selector"""
        try:
            # Try as CSS selector first
            if hasattr(self.page, 'query_selector'):
                selector_method = getattr(self.page, 'query_selector')
                if asyncio.iscoroutinefunction(selector_method):
                    element = await selector_method(target)
                else:
                    element = selector_method(target)
                
                if element:
                    return element
            
            # Try $ method (common in browser libraries)
            if hasattr(self.page, '$'):
                dollar_method = getattr(self.page, '$')
                if asyncio.iscoroutinefunction(dollar_method):
                    element = await dollar_method(target)
                else:
                    element = dollar_method(target)
                
                if element:
                    return element
            
            raise Exception(f"Could not find element: {target}")
            
        except Exception as e:
            raise Exception(f"Element not found: {target} - {str(e)}")
    
    async def _execute_click(self, step: TestStep) -> ExecutionResult:
        """Click an element"""
        try:
            element = await self._find_element(step.target)
            
            # Try different click methods
            if hasattr(element, 'click'):
                click_method = getattr(element, 'click')
                if asyncio.iscoroutinefunction(click_method):
                    await click_method()
                else:
                    click_method()
            else:
                raise Exception(f"Element has no click method")
            
            await asyncio.sleep(1)

            # Post-click validation using expected_result if provided
            if step.expected_result:
                try:
                    # Try treating expected_result as a selector first
                    try:
                        found = await self._find_element(step.expected_result)
                    except Exception:
                        found = None

                    if found:
                        return ExecutionResult(
                            step_number=step.step_number,
                            action=step.action,
                            success=True,
                            message=f"Clicked element: {step.target}; expected element present: {step.expected_result}",
                            actual_result=str(found)
                        )

                    # Fallback: check page text for expected_result
                    page_text = None
                    if hasattr(self.page, 'content'):
                        page_text = await self.page.content()
                    elif hasattr(self.page, 'evaluate'):
                        page_text = await self.page.evaluate('document.body.innerText')

                    if page_text and step.expected_result.lower() in page_text.lower():
                        return ExecutionResult(
                            step_number=step.step_number,
                            action=step.action,
                            success=True,
                            message=f"Clicked element: {step.target}; expected text found",
                            actual_result=step.expected_result
                        )

                    return ExecutionResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=False,
                        message=f"Clicked element: {step.target} but expected_result not satisfied: {step.expected_result}"
                    )
                except Exception as e:
                    return ExecutionResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=False,
                        message=f"Post-click verification failed: {str(e)}"
                    )

            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=True,
                message=f"Clicked element: {step.target}"
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Click failed: {str(e)}"
            )
    
    async def _execute_type(self, step: TestStep) -> ExecutionResult:
        """Type text into an element"""
        try:
            element = await self._find_element(step.target)
            
            # Clear if element has clear method
            if hasattr(element, 'clear'):
                clear_method = getattr(element, 'clear')
                if asyncio.iscoroutinefunction(clear_method):
                    await clear_method()
                else:
                    clear_method()
            
            # Type the value using available methods
            typed = False
            if hasattr(element, 'type'):
                type_method = getattr(element, 'type')
                if asyncio.iscoroutinefunction(type_method):
                    await type_method(step.value or "")
                else:
                    type_method(step.value or "")
                typed = True
            elif hasattr(element, 'fill'):
                fill_method = getattr(element, 'fill')
                if asyncio.iscoroutinefunction(fill_method):
                    await fill_method(step.value or "")
                else:
                    fill_method(step.value or "")
                typed = True
            
            if not typed:
                raise Exception("Element has no type or fill method")
            
            await asyncio.sleep(0.5)
            
            # Post-type validation if expected_result provided
            if step.expected_result:
                try:
                    # Check for expected element or text
                    found = None
                    try:
                        found = await self._find_element(step.expected_result)
                    except Exception:
                        found = None

                    if found:
                        return ExecutionResult(
                            step_number=step.step_number,
                            action=step.action,
                            success=True,
                            message=f"Typed '{step.value}' into {step.target}; expected element present: {step.expected_result}",
                            actual_result=str(found)
                        )

                    page_text = None
                    if hasattr(self.page, 'content'):
                        page_text = await self.page.content()
                    elif hasattr(self.page, 'evaluate'):
                        page_text = await self.page.evaluate('document.body.innerText')

                    if page_text and step.expected_result.lower() in page_text.lower():
                        return ExecutionResult(
                            step_number=step.step_number,
                            action=step.action,
                            success=True,
                            message=f"Typed '{step.value}' into {step.target}; expected text found",
                            actual_result=step.expected_result
                        )

                    return ExecutionResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=False,
                        message=f"Typed '{step.value}' but expected_result not satisfied: {step.expected_result}"
                    )
                except Exception as e:
                    return ExecutionResult(
                        step_number=step.step_number,
                        action=step.action,
                        success=False,
                        message=f"Post-type verification failed: {str(e)}"
                    )

            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=True,
                message=f"Typed '{step.value}' into {step.target}"
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Type failed: {str(e)}"
            )
    
    async def _execute_verify(self, step: TestStep) -> ExecutionResult:
        """Verify element exists or has expected content"""
        try:
            element = await self._find_element(step.target)

            # Prefer planner's expected_result for verification when provided
            comparator = step.expected_result or step.value

            if comparator:
                # Verify element contains expected text
                if hasattr(element, 'text_content'):
                    element_text = await element.text_content()
                elif hasattr(element, 'inner_text'):
                    element_text = await element.inner_text()
                else:
                    element_text = str(element)

                success = comparator.lower() in element_text.lower()
                message = f"Verified '{comparator}' in element" if success else f"Expected '{comparator}' not found in '{element_text}'"
                actual = element_text
            else:
                # Just verify element exists
                success = True
                message = f"Verified element exists: {step.target}"
                actual = None

            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=success,
                message=message,
                actual_result=actual
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Verification failed: {str(e)}"
            )
    
    async def _execute_wait(self, step: TestStep) -> ExecutionResult:
        """Wait for specified seconds or for element"""
        try:
            if step.value and step.value.isdigit():
                seconds = int(step.value)
                await asyncio.sleep(seconds)
                message = f"Waited {seconds} seconds"
            else:
                # Wait for element to appear
                await self.page.wait_for_selector(step.target, timeout=self.wait_timeout)
                message = f"Element appeared: {step.target}"
            
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=True,
                message=message
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Wait failed: {str(e)}"
            )
    
    async def _execute_scroll(self, step: TestStep) -> ExecutionResult:
        """Scroll the page"""
        try:
            if step.value:
                # Scroll specific amount
                if hasattr(self.page, 'evaluate'):
                    await self.page.evaluate(f"window.scrollBy(0, {step.value})")
                message = f"Scrolled {step.value}px"
            else:
                # Scroll to element
                element = await self._find_element(step.target)
                if hasattr(element, 'scroll_into_view_if_needed'):
                    await element.scroll_into_view_if_needed()
                message = f"Scrolled to element: {step.target}"
            
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=True,
                message=message
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step.step_number,
                action=step.action,
                success=False,
                message=f"Scroll failed: {str(e)}"
            )


class VibiumPageAdapter:
    """Adapter for browser objects that act as pages"""
    
    def __init__(self, vibe):
        self._vibe = vibe
        self.url = None

    async def goto(self, url, timeout=None):
        func = getattr(self._vibe, 'goto', None) or getattr(self._vibe, 'go', None)
        if asyncio.iscoroutinefunction(func):
            await func(url)
        else:
            func(url)
        self.url = url

    async def query_selector(self, selector):
        finder = getattr(self._vibe, 'query_selector', None) or getattr(self._vibe, 'find', None)
        if finder is None:
            return None
        if asyncio.iscoroutinefunction(finder):
            return await finder(selector)
        else:
            return finder(selector)

    async def wait_for_selector(self, selector, timeout=None):
        finder = getattr(self._vibe, 'find', None)
        if finder is None:
            raise Exception('wait_for_selector not supported')
        for _ in range(10):
            result = finder(selector) if not asyncio.iscoroutinefunction(finder) else await finder(selector)
            if result:
                return result
            await asyncio.sleep(0.5)
        raise Exception(f'Timeout waiting for selector: {selector}')
