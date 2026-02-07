# conftest.py
# Prevent pytest from attempting to collect non-Python files that begin with 'test_'
# Specifically ignore the generated `test_output.txt` file which is not a test module.
collect_ignore = [
    "test_output.txt",
]
