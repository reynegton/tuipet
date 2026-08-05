import re
from collections import Counter

with open("/tmp/pytest_short.log", "r") as f:
    text = f.read()

# pytest short traceback format:
# ______________________ test_name _______________________
# ... traceback lines ...
# E   ExceptionType: message
exceptions = re.findall(r"^E\s+([^:]+:\s+.*)$", text, re.MULTILINE)

c = Counter(exceptions)
for exc, count in c.most_common(20):
    print(f"{count:3d} {exc[:120]}")
