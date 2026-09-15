from dotenv import dotenv_values
from pathlib import Path
import os

# 环境变量统一管理
config = {
    **dotenv_values(Path(__file__).parent.parent / '.env'),
    **os.environ
}

if __name__ == "__main__":
    # print(config)
    ...
