# test/test_integration.py
import os
import tempfile
import pytest
from expense_manager import User, Storage, ReminderService, Statistics

def test_integration_record_overconsumption():
    """集成测试：添加记录 → 触发过度消费提醒"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'test.json')
        storage = Storage(path)
        
        # 👇 关键：设置足够高的初始余额，避免余额提醒干扰
        storage._data['settings']['initial_balance'] = 5000.0
        storage._data['settings']['threshold_warn'] = 3000.0
        storage._data['settings']['threshold_urgent'] = 1000.0
        storage.save()
        
        user = User(storage)
        reminders = []

        def mock_ui_callback(kind, msg):
            reminders.append((kind, msg))

        # 初始化提醒服务
        reminder_svc = ReminderService(user, ui_callback=mock_ui_callback)
        
        # 等待后台线程可能的初始检查完成（可选，但更稳定）
        import time
        time.sleep(0.1)
        reminders.clear()  # 清除可能的初始余额提醒（防御性）

        # 1. 添加过度消费类别
        user.add_overconsumption_category("饮食")
        
        # 2. 添加非过度消费记录（应无提醒）
        user.add_record(50.0, 'expense', '交通')
        # 不调用 check_overconsumption，所以无提醒
        assert len(reminders) == 0
        
        # 3. 添加过度消费记录 + 手动触发检查
        rec = user.add_record(200.0, 'expense', '饮食')
        reminder_svc.check_overconsumption(rec)
        assert len(reminders) == 1
        assert reminders[0][0] == 'over'
        assert '饮食' in reminders[0][1]
        
        reminder_svc.stop()