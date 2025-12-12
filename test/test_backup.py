# test/test_backup.py
import os
import tempfile
import json
from expense_manager import User, Storage


def test_create_and_restore_backup():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 原始数据
        data_path = os.path.join(tmpdir, 'data.json')
        backup_path = os.path.join(tmpdir, 'backup.json')
        
        storage = Storage(data_path)
        storage._data['settings']['initial_balance'] = 888.0
        storage._data['records'] = [{'id': 'x', 'amount': 100, 'kind': 'expense', 'category': 'test', 'timestamp': 'now', 'note': ''}]
        storage._data['overconsumption_categories'] = ['test']
        storage.save()
        
        user = User(storage)
        # 备份
        user.create_backup(backup_path)
        assert os.path.exists(backup_path)
        
        # 清空原数据
        user.records = []
        user.settings['initial_balance'] = 0
        user.overcats = set()
        
        # 恢复
        user.restore_from_backup(backup_path)
        assert user.get_balance() == 888.0 - 100  # 788.0
        assert 'test' in user.overcats


def test_create_backup_auto_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = os.path.join(tmpdir, 'data.json')
        storage = Storage(data_path)
        storage._data['settings']['initial_balance'] = 100.0
        storage.save()
        user = User(storage)

        # 不传参数，让函数自动生成路径
        backup_path = user.create_backup()
        
        # 验证路径存在且包含 "backup_expense_"
        assert os.path.exists(backup_path)
        assert "backup_expense_" in backup_path


