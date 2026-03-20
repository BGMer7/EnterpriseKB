"""检查 OCR 配置选项"""
from unstructured.partition.utils.ocr_models.ocr_interface import OCR_AGENT_MODULES_WHITELIST
print('Available OCR agents:', OCR_AGENT_MODULES_WHITELIST)

import os
print('\nCurrent OCR_AGENT env:', os.environ.get('OCR_AGENT', 'not set'))
