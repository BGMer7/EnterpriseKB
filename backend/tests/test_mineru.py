import os
import requests

# 切换到项目根目录
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI1MjMwNDg5NCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3NDAxMTE0NiwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTgyMjE4MjEwMDMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI1YzI3NDYwMi1hZGY3LTQ3YzgtODNmMi0xMzdmYjVhMzZlMWUiLCJlbWFpbCI6IiIsImV4cCI6MTc4MTc4NzE0Nn0.S-roeUV4dbtQXvIIqmlsSa5W3NW747LgjVvSoT9PRY4-gUuKgKf1WTEg9BeKUbRaR7c8tkvQWTrZezfHvZv66g"
url = "https://mineru.net/api/v4/file-urls/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"name": "tests/files/1911.05722v3.pdf", "data_id": "1911.05722v3"}
    ],
    "model_version":"vlm"
}
file_path = ["tests/files/1911.05722v3.pdf"]
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print('batch_id:{},urls:{}'.format(batch_id, urls))
            for i in range(0, len(urls)):
                with open(file_path[i], 'rb') as f:
                    res_upload = requests.put(urls[i], data=f)
                    if res_upload.status_code == 200:
                        print(f"{urls[i]} upload success")
                    else:
                        print(f"{urls[i]} upload failed")
        else:
            print('apply upload url failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)