"""
OCR功能完整演示脚本
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processors.parser import DocumentParser


def main():
    print("=" * 60)
    print("OCR 功能演示")
    print("=" * 60)

    # 1. 测试图片OCR
    print("\n📷 1. 图片OCR测试")
    print("-" * 40)

    # 创建一个包含文字的图片用于测试
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img_path = tmp.name

        # 创建图片
        img = Image.new('RGB', (400, 150), color='white')
        draw = ImageDraw.Draw(img)

        # 尝试使用默认字体
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        # 绘制文字
        draw.text((20, 20), "Hello World", fill='black', font=font)
        draw.text((20, 60), "测试OCR功能", fill='black', font=font)
        draw.text((20, 100), "PaddleOCR Demo", fill='black', font=font)

        img.save(img_path)
        print(f"   测试图片已创建: {img_path}")

        # 使用OCR解析图片
        result = DocumentParser.parse(img_path, "png")
        print(f"\n   📝 OCR识别结果:")
        print(f"   {result['content']}")
        print(f"   识别方法: {result['metadata'].get('ocr_method', 'unknown')}")
        print(f"   字符数: {result['metadata'].get('char_count', 0)}")

        # 清理
        os.unlink(img_path)
        print(f"   ✅ 图片OCR测试完成")

    except Exception as e:
        print(f"   ❌ 图片OCR测试失败: {e}")

    # 2. 测试PDF（文本型）
    print("\n\n📄 2. PDF解析测试（文本型PDF）")
    print("-" * 40)
    pdf_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\1911.05722v3.pdf"

    result = DocumentParser.parse(pdf_path, "pdf")
    print(f"   文件: 1911.05722v3.pdf")
    print(f"   类型: 文本型PDF（原生）")
    print(f"   页数: {result['metadata']['page_count']}")
    print(f"   字符数: {len(result['content'])}")
    print(f"   OCR触发: {result['metadata'].get('ocr_used', False)}")
    print(f"   说明: 原生PDF直接提取文本，无需OCR")

    # 3. OCR效果说明
    print("\n\n📋 3. OCR触发条件")
    print("-" * 40)
    print("   当前PDF解析器只在以下情况触发OCR:")
    print("   - PDF文本内容少于50字符（疑似扫描件）")
    print("   - 显式设置 use_ocr=True")
    print("")
    print("   适用场景:")
    print("   - 扫描件PDF（图片型）")
    print("   - 截图/照片")
    print("   - 身份证、发票等证件")

    print("\n" + "=" * 60)
    print("✅ OCR功能演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
