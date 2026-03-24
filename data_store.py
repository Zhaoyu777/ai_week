import json
import os
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
import threading
import re

class DataStore:
    """本地JSON文件数据存储管理类"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.records_file = os.path.join(data_dir, 'records.json')
        self.tags_file = os.path.join(data_dir, 'tags.json')
        self._lock = threading.Lock()
        self.lock_file = os.path.join(data_dir, '.data.lock')
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 初始化数据文件
        self._init_files()
    
    def _init_files(self):
        """初始化数据文件（如果不存在）"""
        if not os.path.exists(self.records_file):
            self._save_json(self.records_file, [])
        if not os.path.exists(self.tags_file):
            # 默认标签
            default_tags = [
                {'id': 1, 'name': '需求开发', 'color': 'primary', 'create_time': self._now()},
                {'id': 2, 'name': '问题记录', 'color': 'danger', 'create_time': self._now()},
                {'id': 3, 'name': '会议纪要', 'color': 'info', 'create_time': self._now()},
                {'id': 4, 'name': '待办事项', 'color': 'warning', 'create_time': self._now()},
                {'id': 5, 'name': '其他', 'color': 'secondary', 'create_time': self._now()}
            ]
            self._save_json(self.tags_file, default_tags)
    
    def _now(self) -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _load_json(self, filepath: str) -> Any:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_json(self, filepath: str, data: Any):
        """保存数据到JSON文件"""
        with self._lock:
            self._acquire_file_lock()
            try:
                file_dir = os.path.dirname(filepath) or '.'
                os.makedirs(file_dir, exist_ok=True)

                fd, temp_path = tempfile.mkstemp(prefix='.json.', dir=file_dir, text=True)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(temp_path, filepath)
                except Exception:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise
            finally:
                self._release_file_lock()

    def _acquire_file_lock(self, timeout_seconds: float = 5.0, sleep_seconds: float = 0.1):
        started_at = time.monotonic()

        while True:
            try:
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                return
            except FileExistsError:
                if time.monotonic() - started_at >= timeout_seconds:
                    raise TimeoutError('数据文件正在被其他请求写入，请稍后重试')
                time.sleep(sleep_seconds)

    def _release_file_lock(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
    
    def _generate_id(self, items: List[Dict]) -> int:
        """生成新的ID"""
        if not items:
            return 1
        return max(item.get('id', 0) for item in items) + 1
    
    def _generate_title(self, content: str) -> str:
        """从内容生成标题"""
        clean_content = re.sub('<[^<]+?>', '', content)
        title = clean_content[:50] + '...' if len(clean_content) > 50 else clean_content
        if not title.strip():
            title = "无标题记录"
        return title
    
    # ==================== 记录操作 ====================
    
    def get_records(self, start_date: Optional[str] = None, 
                    end_date: Optional[str] = None,
                    tag: Optional[str] = None,
                    keyword: Optional[str] = None) -> List[Dict]:
        """获取记录列表，支持筛选"""
        records = self._load_json(self.records_file)
        
        filtered = []
        for record in records:
            # 日期筛选
            if start_date:
                record_date = record.get('create_time', '')[:10]
                if record_date < start_date:
                    continue
            if end_date:
                record_date = record.get('create_time', '')[:10]
                if record_date > end_date:
                    continue
            
            # 标签筛选
            if tag and tag != '全部':
                record_tags = record.get('tag', '')
                # 支持逗号或分号分隔的标签
                tag_list = [t.strip() for t in re.split('[,;]', record_tags)]
                if tag not in tag_list:
                    continue
            
            # 关键词筛选
            if keyword:
                keyword_lower = keyword.lower()
                title = record.get('title', '').lower()
                content = record.get('content', '').lower()
                if keyword_lower not in title and keyword_lower not in content:
                    continue
            
            filtered.append(record)
        
        # 按时间倒序排列
        filtered.sort(key=lambda x: x.get('create_time', ''), reverse=True)
        return filtered
    
    def get_record_by_id(self, record_id: int) -> Optional[Dict]:
        """根据ID获取记录"""
        records = self._load_json(self.records_file)
        for record in records:
            if record.get('id') == record_id:
                return record
        return None
    
    def add_record(self, content: str, tag: str = '其他', 
                   create_time: Optional[str] = None) -> Dict:
        """添加新记录"""
        records = self._load_json(self.records_file)
        
        new_id = self._generate_id(records)
        now = self._now()
        
        record = {
            'id': new_id,
            'title': self._generate_title(content),
            'content': content,
            'tag': tag,
            'create_time': create_time if create_time else now,
            'update_time': now
        }
        
        records.append(record)
        self._save_json(self.records_file, records)
        
        return record
    
    def update_record(self, record_id: int, content: str, 
                      tag: str) -> Optional[Dict]:
        """更新记录"""
        records = self._load_json(self.records_file)
        
        for record in records:
            if record.get('id') == record_id:
                record['title'] = self._generate_title(content)
                record['content'] = content
                record['tag'] = tag
                record['update_time'] = self._now()
                self._save_json(self.records_file, records)
                return record
        
        return None
    
    def delete_record(self, record_id: int) -> bool:
        """删除记录"""
        records = self._load_json(self.records_file)
        
        for i, record in enumerate(records):
            if record.get('id') == record_id:
                records.pop(i)
                self._save_json(self.records_file, records)
                return True
        
        return False
    
    def get_record_counts_by_date(self) -> List[Dict]:
        """获取每日记录数量（用于日历显示）"""
        records = self._load_json(self.records_file)
        
        date_counts = {}
        for record in records:
            date = record.get('create_time', '')[:10]
            if date:
                date_counts[date] = date_counts.get(date, 0) + 1
        
        # 转换为FullCalendar格式
        result = [{'start': date, 'title': str(count)} 
                  for date, count in date_counts.items()]
        return result
    
    # ==================== 标签操作 ====================
    
    def get_tags(self) -> List[Dict]:
        """获取所有标签"""
        return self._load_json(self.tags_file)
    
    def get_tag_by_id(self, tag_id: int) -> Optional[Dict]:
        """根据ID获取标签"""
        tags = self._load_json(self.tags_file)
        for tag in tags:
            if tag.get('id') == tag_id:
                return tag
        return None
    
    def get_tag_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取标签"""
        tags = self._load_json(self.tags_file)
        for tag in tags:
            if tag.get('name') == name:
                return tag
        return None
    
    def add_tag(self, name: str, color: str = 'secondary') -> Dict:
        """添加新标签"""
        tags = self._load_json(self.tags_file)
        
        # 检查是否已存在
        for tag in tags:
            if tag.get('name') == name:
                raise ValueError(f"标签 '{name}' 已存在")
        
        new_id = self._generate_id(tags)
        tag = {
            'id': new_id,
            'name': name,
            'color': color,
            'create_time': self._now()
        }
        
        tags.append(tag)
        self._save_json(self.tags_file, tags)
        
        return tag
    
    def update_tag(self, tag_id: int, name: str, color: str) -> Optional[Dict]:
        """更新标签"""
        tags = self._load_json(self.tags_file)
        
        for tag in tags:
            if tag.get('id') == tag_id:
                tag['name'] = name
                tag['color'] = color
                self._save_json(self.tags_file, tags)
                return tag
        
        return None
    
    def delete_tag(self, tag_id: int) -> bool:
        """删除标签"""
        tags = self._load_json(self.tags_file)
        
        for i, tag in enumerate(tags):
            if tag.get('id') == tag_id:
                tags.pop(i)
                self._save_json(self.tags_file, tags)
                return True
        
        return False
    
    # ==================== 数据迁移 ====================
    
    def import_records(self, records: List[Dict]):
        """批量导入记录（用于数据迁移）"""
        self._save_json(self.records_file, records)
    
    def import_tags(self, tags: List[Dict]):
        """批量导入标签（用于数据迁移）"""
        self._save_json(self.tags_file, tags)
    
    def get_all_data(self) -> Dict:
        """获取所有数据（用于备份）"""
        return {
            'records': self._load_json(self.records_file),
            'tags': self._load_json(self.tags_file),
            'export_time': self._now()
        }
    
    def restore_data(self, data: Dict):
        """恢复数据（用于还原）"""
        if 'records' in data:
            self._save_json(self.records_file, data['records'])
        if 'tags' in data:
            self._save_json(self.tags_file, data['tags'])


# 全局数据存储实例
data_store = DataStore()
