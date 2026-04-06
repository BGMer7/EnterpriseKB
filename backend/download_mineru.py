import os
from modelscope.hub.snapshot_download import snapshot_download

# 目标路径（注意：这里我直接加上了 /models，一步到位）
target_dir = "D:/DevKits/MinerU_Models/models"
os.makedirs(target_dir, exist_ok=True)

print("🚀 开始从 ModelScope (魔搭) 下载 MinerU 全量模型...")
print("提示：这次下载的是真实文件，不是快捷方式，速度会很快！")

try:
    # OpenDataLab 官方在魔搭上的最新模型仓库
    snapshot_download(
        'OpenDataLab/PDF-Extract-Kit-1.0', 
        local_dir=target_dir,
        # 这里最关键：如果不加参数，某些版本默认也会报错
    )
    print(f"\n✅ 下载成功！请去 {target_dir} 检查是否真的有几十个文件了。")
    
except Exception as e:
    print(f"\n❌ 下载出错: {e}")