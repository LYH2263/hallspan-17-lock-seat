import os
import tempfile

# 必须在任何 app 模块导入之前指向 sqlite，否则 engine 会按默认 postgres 建连
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp(prefix='hallspan-test-')}/test.db")
