# utils/color_utils.py
"""
彩色输出工具，从main_color.py提取
"""
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True, strip=False)
    
    # 定义颜色快捷方式
    R = Fore.RED
    G = Fore.GREEN
    Y = Fore.YELLOW
    B = Fore.BLUE
    M = Fore.MAGENTA
    C = Fore.CYAN
    W = Fore.WHITE
    RS = Style.RESET_ALL
    
    # 定义样式
    BOLD = Style.BRIGHT
    DIM = Style.DIM
    
    COLOR_ENABLED = True
except ImportError:
    COLOR_ENABLED = False
    R = G = Y = B = M = C = W = RS = BOLD = DIM = ""

def print_color(text, color_code):
    """打印带颜色的文本"""
    if COLOR_ENABLED:
        return f"{color_code}{text}{RS}"
    return text

def print_colored_banner(text, color_code=G):
    """打印彩色横幅（带装饰边框）"""
    border = "=" * (len(text) + 8)
    banner = f"\n{border}\n    {text}\n{border}\n"
    print(print_color(banner, color_code))

def print_success(text):
    """打印成功信息（绿色）"""
    print(print_color(text, G))

def print_warning(text):
    """打印警告信息（黄色）"""
    print(print_color(text, Y))

def print_error(text):
    """打印错误信息（红色）"""
    print(print_color(text, R))

def print_info(text):
    """打印信息（蓝色）"""
    print(print_color(text, B))

def print_highlight(text):
    """打印高亮信息（洋红色）"""
    print(print_color(text, M))