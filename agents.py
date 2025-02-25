from zswarm import Swarm, Agent
import streamlit as st
import os
import json

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

client = Swarm()

def newspaper_summarizer(text):
    summerizer = Agent(
        name="Summarizer",
        model="gemini/gemini-2.0-flash-thinking-exp-01-21",
        instructions = """
        Tóm tắt văn bản sau bằng cách phân loại và cấu trúc các tin tức theo định dạng JSON schema rõ ràng. 

        ### **1. Phân loại:**  
        "scale": "VN" (tin tức về Việt Nam) hoặc "others" (quốc tế).
        "category": "Chính trị", "Kinh tế", hoặc "Tài chính".

        ### **2. Ví dụ đầu ra phải bắt buộc là 1 phần tử JSON schema duy nhất có dạng y hệt dưới đây:**
        {
        "scale": "VN",
        "category": "Kinh tế",
        "content": "- GDP Việt Nam tăng ....\n- Tăng trưởng ....\n- Doanh thu ...." 
        }
        
        ### **3. Yêu cầu về trình bày:**
        - Nếu bài báo thuộc nhiều lĩnh vực, chỉ chọn một lĩnh vực chính để trình bày trong 1 JSON schema duy nhất.
        - Content chỉ chứa nội dung tóm tắt từ văn bản gốc và không được phép bịa thông tin.  
        - Không được sử dụng dấu ngoặc kép `"` trong value của bất kỳ trường nào. Nếu có cụm từ cần nhấn mạnh, hãy dùng dấu nháy đơn `'` thay vì dấu `"` hoặc mô tả lại theo cách khác.
        Lưu ý:  
        - Kết quả cuối cùng phải là 1 phần tử JSON schema duy nhất
        - Kết quả KHÔNG được phép là 1 list chứa nhiều JSON schema.
        """,
        functions=[],
        model_config={
                "temperature": 0,
                }
    )

    response = client.run(
        agent=summerizer,
        messages=[{"role": "user", "content": text}],
    )

    res = response.messages[-1]["content"].replace("`", "").replace("json", "").replace("*", "").strip()
    print(res)
    return json.loads(res, strict = False)
