# ============================================================
# 常量表（预计算）
# ============================================================

# 密钥循环左移位数
KEY_SHIFTS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]

# PC-2：从 56 位 key 中选出 48 位子密钥
PC2 = [
    13, 16, 10, 23, 0, 4, 2, 27, 14, 5, 20, 9, 22, 18, 11, 3,
    25, 7, 15, 6, 26, 19, 12, 1, 40, 51, 30, 36, 46, 54, 29, 39,
    50, 44, 32, 47, 43, 48, 38, 55, 33, 52, 45, 41, 49, 35, 28, 31
]

# 初始置换 IP
IP = [
    57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7,
    56, 48, 40, 32, 24, 16, 8, 0, 58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38, 30, 22, 14, 6
]

# 逆初始置换 FP
FP = [
    39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27, 34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41, 9, 49, 17, 57, 25, 32, 0, 40, 8, 48, 16, 56, 24
]

# 扩展置换 E
E = [
    31, 0, 1, 2, 3, 4, 3, 4, 5, 6, 7, 8,
    7, 8, 9, 10, 11, 12, 11, 12, 13, 14, 15, 16,
    15, 16, 17, 18, 19, 20, 19, 20, 21, 22, 23, 24,
    23, 24, 25, 26, 27, 28, 27, 28, 29, 30, 31, 0
]

# P 置换
P = [
    15, 6, 19, 20, 28, 11, 27, 16,
    0, 14, 22, 25, 4, 17, 30, 9,
    1, 7, 23, 13, 31, 26, 2, 8,
    18, 12, 29, 5, 21, 10, 3, 24
]

# S 盒
S_BOXES = [
    # S1
    [[14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7],
     [0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8],
     [4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0],
     [15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13]],
    # S2
    [[15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10],
     [3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5],
     [0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15],
     [13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9]],
    # S3
    [[10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8],
     [13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1],
     [13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7],
     [1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12]],
    # S4
    [[7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15],
     [13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9],
     [10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4],
     [3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14]],
    # S5
    [[2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9],
     [14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6],
     [4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14],
     [11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3]],
    # S6
    [[12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11],
     [10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8],
     [9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6],
     [4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13]],
    # S7
    [[4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1],
     [13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6],
     [1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2],
     [6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12]],
    # S8
    [[13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7],
     [1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2],
     [7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8],
     [2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11]],
]

# 十六进制映射
HEX2BIN = {c: format(i, '04b') for i, c in enumerate('0123456789ABCDEF')}
BIN2HEX = {v: k for k, v in HEX2BIN.items()}


# ============================================================
# 基础工具
# ============================================================

def str_to_bt(input_str):
    """字符串 -> 64 位二进制列表"""
    s = input_str[:4]
    bits = ''.join(format(ord(c), '016b') for c in s)
    return [int(b) for b in bits.ljust(64, '0')]


def bt64_to_hex(byte_data):
    """64 位二进制列表 -> 16 位十六进制字符串"""
    return ''.join(BIN2HEX[''.join(map(str, byte_data[i:i+4]))] for i in range(0, 64, 4))


def hex_to_bt64(hex_str):
    """16 位十六进制字符串 -> 64 位二进制列表"""
    return ''.join(HEX2BIN[c] for c in hex_str[:16])


# ============================================================
# DES 核心
# ============================================================

def generate_keys(key_byte):
    """从 64 位密钥生成 16 个 48 位子密钥"""
    # 密钥置换选择 PC-1
    key = [0] * 56
    for i in range(7):
        for j in range(8):
            key[i * 8 + j] = key_byte[8 * (7 - j) + i]

    keys = []
    for shift in KEY_SHIFTS:
        # 循环左移
        for _ in range(shift):
            temp_left, temp_right = key[0], key[28]
            for k in range(27):
                key[k] = key[k + 1]
                key[28 + k] = key[29 + k]
            key[27] = temp_left
            key[55] = temp_right
        # PC-2 压缩置换
        keys.append([key[pos] for pos in PC2])
    return keys


def init_permute(original_data):
    """初始置换 IP"""
    ip_byte = [0] * 64
    for i in range(4):
        for j in range(7, -1, -1):
            ip_byte[i * 8 + 7 - j] = original_data[j * 8 + i * 2 + 1]
            ip_byte[i * 8 + 7 - j + 32] = original_data[j * 8 + i * 2]
    return ip_byte


def expand_permute(right_data):
    """扩展置换 E"""
    return [right_data[i] for i in E]


def s_box_permute(expand_byte):
    """S 盒置换"""
    s_box_byte = [0] * 32
    for m in range(8):
        i = expand_byte[m * 6] * 2 + expand_byte[m * 6 + 5]
        j = (expand_byte[m * 6 + 1] << 3) | (expand_byte[m * 6 + 2] << 2) \
            | (expand_byte[m * 6 + 3] << 1) | expand_byte[m * 6 + 4]
        val = S_BOXES[m][i][j]
        for n in range(4):
            s_box_byte[m * 4 + n] = (val >> (3 - n)) & 1
    return s_box_byte


def p_permute(s_box_byte):
    """P 置换"""
    return [s_box_byte[i] for i in P]


def finally_permute(end_byte):
    """逆初始置换 FP"""
    return [end_byte[i] for i in FP]


def xor(a, b):
    return [x ^ y for x, y in zip(a, b)]


def _des_crypt(data_byte, keys, reverse=False):
    """DES 加密/解密核心（reverse=True 时密钥倒序，用于解密）"""
    ip_byte = init_permute(data_byte)
    left, right = ip_byte[:32], ip_byte[32:]

    key_order = reversed(keys) if reverse else keys
    for key in key_order:
        temp_left = left
        left = right
        f = p_permute(s_box_permute(xor(expand_permute(right), key)))
        right = xor(f, temp_left)

    final_data = right + left
    return finally_permute(final_data)


def enc(data_byte, key_byte):
    """标准 DES 加密"""
    return _des_crypt(data_byte, generate_keys(key_byte))


def dec(data_byte, key_byte):
    """标准 DES 解密"""
    return _des_crypt(data_byte, generate_keys(key_byte), reverse=True)


# ============================================================
# 密钥派生与多轮加密
# ============================================================

def get_key_bytes(key):
    """密钥字符串 -> 多个 64 位密钥块"""
    key_bytes = []
    iterator = len(key) // 4
    remainder = len(key) % 4
    for i in range(iterator):
        key_bytes.append(str_to_bt(key[i * 4:i * 4 + 4]))
    if remainder > 0:
        key_bytes.append(str_to_bt(key[iterator * 4:]))
    return key_bytes


def _apply_keys(block, key_blocks):
    """对单个 64 位数据块，依次用所有密钥块做 DES 加密"""
    for kb in key_blocks:
        block = enc(block, kb)
    return block


def strEnc(data, firstKey, secondKey, thirdKey):
    """
    与原版 strEnc 行为完全一致的多轮 DES 加密。
    """
    # 收集密钥块
    key1 = get_key_bytes(firstKey) if firstKey else []
    key2 = get_key_bytes(secondKey) if secondKey else []
    key3 = get_key_bytes(thirdKey) if thirdKey else []

    if not data:
        return ""

    # 按 4 字符一组分块
    blocks = []
    iterator = len(data) // 4
    remainder = len(data) % 4

    for i in range(iterator):
        blocks.append(data[i * 4:i * 4 + 4])
    if remainder > 0:
        blocks.append(data[iterator * 4:])

    enc_data = ""
    for block_str in blocks:
        bt = str_to_bt(block_str)
        bt = _apply_keys(bt, key1)
        bt = _apply_keys(bt, key2)
        bt = _apply_keys(bt, key3)
        enc_data += bt64_to_hex(bt)

    return enc_data

resultx = strEnc("test", "key1", "key2", "key3")
print(resultx)
