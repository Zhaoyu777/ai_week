from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from config import Config
from datetime import datetime
import base64
from openai import OpenAI
from data_store import data_store
from logic.ai_config_logic import ai_config_logic

import httpx

os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

app = Flask(__name__)
app.config.from_object(Config)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/settings/ai', methods=['GET'])
def get_ai_settings():
    settings = ai_config_logic.get_config()
    return jsonify(settings)


@app.route('/api/settings/ai', methods=['PUT'])
def update_ai_settings():
    data = request.json or {}

    try:
        settings = ai_config_logic.update_config(data, app.config)
        app.logger.info(
            'AI settings updated, text_model=%s, vision_model=%s',
            settings['text_model'],
            settings['vision_model']
        )
        return jsonify({
            'message': 'AI配置保存成功',
            'data': settings
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except TimeoutError as e:
        app.logger.warning('AI settings update timeout: %s', str(e))
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        app.logger.exception('AI settings update failed: %s', str(e))
        return jsonify({'error': 'AI配置保存失败，请稍后重试'}), 500

@app.route('/api/ocr', methods=['POST'])
def ocr_image():
    if 'image' not in request.files:
        return jsonify({'error': '未上传图片'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
        
    try:
        # Convert image to base64
        image_content = file.read()
        base64_image = base64.b64encode(image_content).decode('utf-8')
        image_url = f"data:image/png;base64,{base64_image}"
        
        api_key = app.config['ALIYUN_API_KEY']
        if not api_key:
            return jsonify({'error': '未配置 AI API Key'}), 500
            
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=httpx.Client(proxy=None)
        )
        
        completion = client.chat.completions.create(
            model=app.config['ALIYUN_VL_MODEL'],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            },
                        },
                        {"type": "text", "text": "请分析图片内容，提取关键信息并整理为清晰的业务记录。请严格按照以下格式输出：\n\n【提问者】【问题描述】\n(简明扼要地描述业务问题或需求背景)\n\n【解决方案/处理结果】\n(详细描述处理过程、结论或待办事项)\n\n注意：如果图片中没有明确的问题或解决方案，请根据内容进行合理推断和总结。直接输出整理后的内容，不要包含任何客套话。"},
                    ],
                },
            ],
        )

        extracted_text = completion.choices[0].message.content
        return jsonify({'text': extracted_text})

    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return jsonify({'error': f"图片识别失败: {str(e)}"}), 500

@app.route('/api/record-counts', methods=['GET'])
def get_record_counts():
    """获取每日记录数量（用于日历显示）"""
    counts = data_store.get_record_counts_by_date()
    return jsonify(counts)

@app.route('/api/tags', methods=['GET'])
def get_tags():
    """获取所有标签"""
    tags = data_store.get_tags()
    return jsonify(tags)

@app.route('/api/tags', methods=['POST'])
def add_tag():
    """添加新标签"""
    data = request.json
    name = data.get('name')
    color = data.get('color', 'secondary')
    
    if not name:
        return jsonify({'error': '标签名称不能为空'}), 400
    
    try:
        tag = data_store.add_tag(name, color)
        return jsonify({'id': tag['id'], 'message': '标签添加成功'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/tags/<int:id>', methods=['PUT'])
def update_tag(id):
    """更新标签"""
    data = request.json
    name = data.get('name')
    color = data.get('color')
    
    tag = data_store.update_tag(id, name, color)
    if tag:
        return jsonify({'message': '标签更新成功'})
    else:
        return jsonify({'error': '标签不存在'}), 404

@app.route('/api/tags/<int:id>', methods=['DELETE'])
def delete_tag(id):
    """删除标签"""
    success = data_store.delete_tag(id)
    if success:
        return jsonify({'message': '标签删除成功'})
    else:
        return jsonify({'error': '标签不存在'}), 404

@app.route('/api/records', methods=['GET'])
def get_records():
    """获取记录列表，支持筛选"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tag = request.args.get('tag')
    keyword = request.args.get('keyword')
    
    records = data_store.get_records(
        start_date=start_date,
        end_date=end_date,
        tag=tag,
        keyword=keyword
    )
    
    return jsonify(records)

@app.route('/api/records', methods=['POST'])
def add_record():
    """添加新记录"""
    data = request.json
    content = data.get('content')
    tag = data.get('tag', '其他')
    create_time = data.get('create_time')

    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    
    record = data_store.add_record(
        content=content,
        tag=tag,
        create_time=create_time
    )
    
    return jsonify({'id': record['id'], 'message': '记录添加成功'}), 201

@app.route('/api/records/<int:id>', methods=['PUT'])
def update_record(id):
    """更新记录"""
    data = request.json
    content = data.get('content')
    tag = data.get('tag')
    
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    
    record = data_store.update_record(id, content, tag)
    if record:
        return jsonify({'message': '记录更新成功'})
    else:
        return jsonify({'error': '记录不存在'}), 404

@app.route('/api/records/<int:id>', methods=['DELETE'])
def delete_record(id):
    """删除记录"""
    success = data_store.delete_record(id)
    if success:
        return jsonify({'message': '记录删除成功'})
    else:
        return jsonify({'error': '记录不存在'}), 404

@app.route('/api/report', methods=['POST'])
def generate_report():
    """生成周报"""
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': '请选择开始和结束日期'}), 400
    
    # 获取记录
    records = data_store.get_records(start_date=start_date, end_date=end_date)
    
    if not records:
        return jsonify({'success': False, 'report': '该时间段内没有工作记录，无法生成周报。'})
    
    # 按时间正序排列
    records.sort(key=lambda x: x.get('create_time', ''))
    
    # 准备提示文本
    records_text = ""
    for r in records:
        create_time = r.get('create_time', '')
        tag = r.get('tag', '')
        title = r.get('title', '')
        content = r.get('content', '')
        records_text += f"- [{create_time[:10]}] 【{tag}】 {title}: {content}\n"
    
    prompt = f"""
请根据以下工作记录生成一份专业的周报：

时间范围：{start_date} 到 {end_date}

工作记录：
{records_text}

要求：
1. 包含本周完成工作。
2. 语言简练专业。
3. 适当润色，合并同类项。
4. 无需生成下周计划

周报示例：
1. 系统功能维护与问题修复
● 处理 安徽分校河南分校不进行发放功能调整。
● 重庆分校宿舍学员添加产品
2. 学员交付支撑
● 广西排课直播调整（排查删除重排导致异常）
● 广西合作院校班级学员导入
3. 系统特殊修改与问题处理
● 广西学员数据统计
4. 版本上线
● YLC-AMS-v0.1 埋点&学情档案 版本开发
"""

    # 调用 AI API
    api_key = app.config['ALIYUN_API_KEY']
    if not api_key:
        return jsonify({'success': False, 'report': '未配置AI API Key，仅展示聚合数据：\n\n' + records_text})
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=httpx.Client(proxy=None)
        )
        
        completion = client.chat.completions.create(
            model=app.config['ALIYUN_MODEL'],
            messages=[
                {"role": "system", "content": "你是一个专业的职场助手，擅长撰写周报。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        report_content = completion.choices[0].message.content
        return jsonify({'success': True, 'content': report_content})
            
    except Exception as e:
        return jsonify({'success': False, 'report': str(e)}), 500


# ==================== 数据备份与恢复 API ====================

@app.route('/api/backup', methods=['GET'])
def backup_data():
    """备份所有数据"""
    data = data_store.get_all_data()
    return jsonify(data)

@app.route('/api/restore', methods=['POST'])
def restore_data():
    """恢复数据"""
    data = request.json
    try:
        data_store.restore_data(data)
        return jsonify({'message': '数据恢复成功'})
    except Exception as e:
        return jsonify({'error': f'数据恢复失败: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5100)
