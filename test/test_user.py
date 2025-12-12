# test/test_user.py
import os
import tempfile
import pytest
from expense_manager import User, Storage, Record

def test_get_balance_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'test.json')
        storage = Storage(path)
        storage._data['settings']['initial_balance'] = 1000.0
        storage.save()
        user = User(storage)
        assert user.get_balance() == 1000.0

def test_get_balance_with_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'test.json')
        storage = Storage(path)
        storage._data['settings']['initial_balance'] = 500.0
        storage._data['records'] = [
            {'id': '1', 'amount': 200.0, 'kind': 'income', 'category': 'salary', 'timestamp': '2025-01-01T12:00:00', 'note': ''},
            {'id': '2', 'amount': 150.0, 'kind': 'expense', 'category': 'food', 'timestamp': '2025-01-02T12:00:00', 'note': ''}
        ]
        storage.save()
        user = User(storage)
        assert user.get_balance() == 500 + 200 - 150  # 550.0