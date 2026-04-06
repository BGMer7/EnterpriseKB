import ollama
from PIL import Image
import os
import sys

def test_qwen_vl(image_path, prompt):
    # 1. 检查模型是否存在
    model_name = "qwen2.5vl:7b"  # 确保和你下载的模型名称一致
    
    try:
        # 检查本地是否有该模型
        ollama.show(model_name)
        print(f"✅ 模型 '{model_name}' 已就绪。")
    except Exception as e:
        print(f"❌ 错误：未找到模型 '{model_name}'。请先运行 'ollama run {model_name}' 下载。")
        print(f"详细错误: {e}")
        return

    # 2. 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误：找不到图片文件 '{image_path}'")
        return

    print(f"🖼️  正在加载图片: {image_path}")
    print(f"💬 用户问题: {prompt}")
    print("-" * 30)

    try:
        # 3. 调用模型 (流式输出，体验更好)
        # 注意：ollama python 库可以直接接受文件路径字符串作为 image 参数
        stream = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_path] 
            }],
            stream=True
        )

        print("🤖 模型回答:\n")
        full_response = ""
        
        # 逐块打印回答
        for chunk in stream:
            content = chunk['message']['content']
            print(content, end='', flush=True)
            full_response += content
            
        print("\n" + "-" * 30)
        print("✅ 回答完成。")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        print("提示：请确保 Ollama 服务正在运行 (通常在后台自动运行)。")

if __name__ == "__main__":
    # --- 配置区域 ---
    
    # 方法 A: 直接在代码里修改图片路径
    # 请将下面的路径改为你电脑上真实存在的图片路径
    # 例如: r"C:\Users\19377\Pictures\test.jpg" (注意前面的 r 防止转义字符问题)
    my_image_path = r"files\qwenvl-test.png" 
    
    # 方法 B: 或者通过命令行参数传入图片路径
    # 用法: python test_qwen_vl.py C:\path\to\your\image.png
    if len(sys.argv) > 1:
        my_image_path = sys.argv[1]
    
    # 如果文件不存在，创建一个简单的测试提示，让用户知道要改哪里
    if not os.path.exists(my_image_path) and len(sys.argv) == 1:
        print(f"⚠️  提示：默认图片 '{my_image_path}' 不存在。")
        print("请编辑脚本中的 'my_image_path' 变量，或者在命令行运行时传入图片路径：")
        print(f"   python {os.path.basename(__file__)} C:\\你的\\图片\\路径.jpg")
        print("-" * 30)
        # 为了演示，我们可以尝试找一个系统自带的图片，或者让用户输入
        # 这里我们暂停，等待用户确认或修改
        user_input = input("按回车键退出，或输入正确的图片路径继续: ")
        if user_input and os.path.exists(user_input):
            my_image_path = user_input
        else:
            print("未提供有效图片，程序退出。")
            sys.exit(0)

    # 定义你的问题
    my_question = "这张图片里有什么？请详细描述图中的内容、颜色和任何可见的文字。"

    # 开始运行
    test_qwen_vl(my_image_path, my_question)