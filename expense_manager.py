
#!/usr/bin/env python3
# expense_manager.py
# A desktop personal finance (记账本) app implemented in Python with Tkinter.
# Implements classes: User, Record, LoanRecord, Statistics, ReminderService, UIController
# Persistence: local JSON file (data.json)
# Author: generated with ChatGPT assistance
# License: MIT
import json
import threading
import uuid
import datetime
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# ----------------------------- Data Models ----------------------------------

#生成当前时间的 ISO 格式字符串
def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec='seconds')

@dataclass
class Record:
    #表示单条收支记录的数据结构
    """A single income/expense record."""
    id: str
    amount: float
    kind: str  # 'income' or 'expense'
    category: str
    timestamp: str  # ISO string
    note: str = ''
    overconsumption_mark: bool = False

    #将 Record 对象转换为字典，用于 JSON 序列化
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    #从字典创建 Record 对象，用于 JSON 反序列化
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Record':
        return Record(**d)


@dataclass
class LoanRecord:
    #表示借款记录的数据结构
    """A loan/IOU record."""
    id: str
    name: str  # who borrowed
    amount: float
    loan_date: str
    due_date: Optional[str] = None
    repaid: bool = False
    note: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'LoanRecord':
        return LoanRecord(**d)


# ----------------------------- Business Logic --------------------------------

class Storage:
    """Simple JSON file storage for records and settings."""
    #初始化存储对象，设置数据文件路径和默认数据结构
    def __init__(self, path: str = 'data.json'):
        self.path = path
        self._data = {
            'records': [],
            'loans': [],
            'settings': {
                'initial_balance': 0.0,
                'threshold_warn': 3000.0,
                'threshold_urgent': 1000.0,
                'reminder_enabled': False,
                'reminder_time': '20:00'  # HH:MM
            },
            'overconsumption_categories': []
        }
        self._load()

    #从 JSON 文件加载数据，如果文件不存在则使用默认数据
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._data.update(data)
            except Exception as e:
                print("Failed to load storage:", e)

    #将当前数据保存到 JSON 文件
    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to save storage:", e)

    #获取/设置收支记录和借款记录
    # Records
    def get_records(self) -> List[Record]:
        return [Record.from_dict(d) for d in self._data.get('records', [])]

    def set_records(self, records: List[Record]):
        self._data['records'] = [r.to_dict() for r in records]
        self.save()

    def get_loans(self) -> List[LoanRecord]:
        return [LoanRecord.from_dict(d) for d in self._data.get('loans', [])]

    def set_loans(self, loans: List[LoanRecord]):
        self._data['loans'] = [l.to_dict() for l in loans]
        self.save()

    #设置相关方法
    def get_settings(self) -> Dict[str, Any]:
        return self._data.get('settings', {})

    def update_settings(self, settings: Dict[str, Any]):
        self._data['settings'].update(settings)
        self.save()

    def get_overconsumption_categories(self) -> List[str]:
        return self._data.get('overconsumption_categories', [])

    def set_overconsumption_categories(self, cats: List[str]):
        self._data['overconsumption_categories'] = cats
        self.save()


class User:
    """Represents a user who manages records and loans."""
    def __init__(self, storage: Storage):
        self.storage = storage
        self.records: List[Record] = storage.get_records()
        self.loans: List[LoanRecord] = storage.get_loans()
        self.settings = storage.get_settings()
        self.overcats = set(storage.get_overconsumption_categories())

    # Record operations
    def add_record(self, amount: float, kind: str, category: str, timestamp: Optional[str] = None, note: str = '') -> Record:
        '''
        功能: 添加新的收支记录
        参数: 金额、类型(income/expense)、类别、时间、备注
        返回: 新创建的 Record 对象
        '''
        rid = str(uuid.uuid4())
        ts = timestamp or now_iso()
        rec = Record(id=rid, amount=float(amount), kind=kind, category=category, timestamp=ts, note=note,
                     overconsumption_mark=(category in self.overcats))
        self.records.append(rec)
        self.storage.set_records(self.records)
        return rec

    def update_record(self, record_id: str, **kwargs) -> Optional[Record]:
        '''
        功能: 更新指定ID的记录
        参数: 记录ID和要更新的字段键值对
        返回: 更新后的记录对象或None(如果未找到)
        '''
        for r in self.records:
            if r.id == record_id:
                for k, v in kwargs.items():
                    if hasattr(r, k):
                        setattr(r, k, v)
                self.storage.set_records(self.records)
                return r
        return None

    def delete_record(self, record_id: str) -> bool:
        orig = len(self.records)
        self.records = [r for r in self.records if r.id != record_id]
        changed = len(self.records) != orig
        if changed:
            self.storage.set_records(self.records)
        return changed

    # Loan operations
    def add_loan(self, name: str, amount: float, loan_date: Optional[str] = None, due_date: Optional[str] = None, note: str = '') -> LoanRecord:
        lid = str(uuid.uuid4())
        loan_date = loan_date or now_iso()
        loan = LoanRecord(id=lid, name=name, amount=float(amount), loan_date=loan_date, due_date=due_date, note=note)
        self.loans.append(loan)
        self.storage.set_loans(self.loans)
        return loan

    #标记借款为已还款状态
    def mark_loan_repaid(self, loan_id: str) -> bool:
        for l in self.loans:
            if l.id == loan_id:
                l.repaid = True
                self.storage.set_loans(self.loans)
                return True
        return False

    def delete_loan(self, loan_id: str) -> bool:
        orig = len(self.loans)
        self.loans = [l for l in self.loans if l.id != loan_id]
        changed = len(self.loans) != orig
        if changed:
            self.storage.set_loans(self.loans)
        return changed

    # Settings and overconsumption categories
    #设置余额预警阈值
    def set_thresholds(self, warn: float, urgent: float):
        self.settings['threshold_warn'] = float(warn)
        self.settings['threshold_urgent'] = float(urgent)
        self.storage.update_settings(self.settings)

    #设置初始余额
    def set_initial_balance(self, amount: float):
        self.settings['initial_balance'] = float(amount)
        self.storage.update_settings(self.settings)

    #添加/移除过度消费类别
    def add_overconsumption_category(self, cat: str):
        self.overcats.add(cat)
        self.storage.set_overconsumption_categories(list(self.overcats))

    def remove_overconsumption_category(self, cat: str):
        if cat in self.overcats:
            self.overcats.remove(cat)
            self.storage.set_overconsumption_categories(list(self.overcats))

    #计算当前余额
    def get_balance(self) -> float:
        # balance = initial_balance + sum(incomes) - sum(expenses)
        bal = float(self.settings.get('initial_balance', 0.0))
        for r in self.records:
            if r.kind == 'income':
                bal += r.amount
            else:
                bal -= r.amount
        return bal
    def create_backup(self, backup_path: str = None) -> str:
        if backup_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_expense_{timestamp}.json"
        try:
            backup_data = {
                'records': [r.to_dict() for r in self.records],
                'loans': [l.to_dict() for l in self.loans],
                'settings': self.settings,
                'overconsumption_categories': list(self.overcats),
                'backup_time': now_iso(),
                'version': '1.0'
            }
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            return backup_path
        except Exception as e:
            raise Exception(f"备份失败: {str(e)}")
    def restore_from_backup(self, backup_path: str) -> bool:
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            required_keys = ['records', 'loans', 'settings']
            if not all(key in backup_data for key in required_keys):
                raise ValueError("无效的备份文件格式")
            # 恢复数据 → 直接赋值给 self，不是 self.user
            self.records = [Record.from_dict(d) for d in backup_data['records']]
            self.loans = [LoanRecord.from_dict(d) for d in backup_data['loans']]
            self.settings.update(backup_data['settings'])
            if 'overconsumption_categories' in backup_data:
                self.overcats = set(backup_data['overconsumption_categories'])
            # 保存到 storage
            self.storage.set_records(self.records)
            self.storage.set_loans(self.loans)
            self.storage.update_settings(self.settings)
            self.storage.set_overconsumption_categories(list(self.overcats))
            return True
        except Exception as e:
            raise Exception(f"恢复失败: {str(e)}")

#统计类
class Statistics:
    """Compute statistics (total income/expense, category breakdowns, monthly series)."""
    def __init__(self, user: User):
        self.user = user

    #计算指定时间范围内的总收入、总支出和余额
    def totals(self, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, float]:
        income = 0.0
        expense = 0.0
        recs = self.filter_records(start, end)
        for r in recs:
            if r.kind == 'income':
                income += r.amount
            else:
                expense += r.amount
        return {'income': income, 'expense': expense, 'balance': income - expense + float(self.user.settings.get('initial_balance', 0.0))}

    #按类别统计支出分布，收入统一归到"Income"类别
    def category_breakdown(self, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, float]:
        buckets: Dict[str, float] = {}
        recs = self.filter_records(start, end)
        for r in recs:
            buckets.setdefault(r.category, 0.0)
            if r.kind == 'expense':
                buckets[r.category] += r.amount
            else:
                # include income under 'Income' bucket
                buckets.setdefault('Income', 0.0)
                buckets['Income'] += r.amount
        return buckets

    #生成最近N个月的月度收支序列数据
    def monthly_series(self, months: int = 6) -> List[Tuple[str, float, float]]:
        """Return last `months` months series of (month_label, income, expense)."""
        today = datetime.date.today()
        results: List[Tuple[str, float, float]] = []
        for i in range(months-1, -1, -1):
            first = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
            # compute month offset
            y = today.year
            m = today.month - i
            while m <= 0:
                y -= 1
                m += 12
            start = datetime.date(y, m, 1)
            if m == 12:
                end = datetime.date(y+1, 1, 1)
            else:
                end = datetime.date(y, m+1, 1)
            start_iso = datetime.datetime.combine(start, datetime.time.min).isoformat()
            end_iso = datetime.datetime.combine(end, datetime.time.min).isoformat()
            inc = 0.0
            exp = 0.0
            for r in self.filter_records(start_iso, end_iso):
                if r.kind == 'income':
                    inc += r.amount
                else:
                    exp += r.amount
            results.append((start.strftime('%Y-%m'), inc, exp))
        return results

    #根据时间范围过滤记录
    def filter_records(self, start: Optional[str] = None, end: Optional[str] = None) -> List[Record]:
        recs = self.user.records
        if start:
            recs = [r for r in recs if r.timestamp >= start]
        if end:
            recs = [r for r in recs if r.timestamp < end]
        return recs
    def yearly_summary(self, year: int = None) -> Dict[str, Any]:
        """获取年度收支总结，包括月度趋势和分类占比"""
        if year is None:
            year = datetime.datetime.now().year
        
        start_date = f"{year}-01-01T00:00:00"
        end_date = f"{year+1}-01-01T00:00:00"
        
        year_records = self.filter_records(start_date, end_date)
        
        monthly_data = []
        for month in range(1, 13):
            month_start = f"{year}-{month:02d}-01T00:00:00"
            if month == 12:
                month_end = f"{year+1}-01-01T00:00:00"
            else:
                month_end = f"{year}-{month+1:02d}-01T00:00:00"
            
            month_records = self.filter_records(month_start, month_end)
            month_income = sum(r.amount for r in month_records if r.kind == 'income')
            month_expense = sum(r.amount for r in month_records if r.kind == 'expense')
            monthly_data.append({
                'month': f"{year}-{month:02d}",
                'income': month_income,
                'expense': month_expense,
                'balance': month_income - month_expense
            })
        
        total_income = sum(r.amount for r in year_records if r.kind == 'income')
        total_expense = sum(r.amount for r in year_records if r.kind == 'expense')
        
        return {
            'year': year,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': total_income - total_expense,
            'monthly_trend': monthly_data,
            'category_breakdown': self.category_breakdown(start_date, end_date)
        }


class ReminderService:
    """Handles checking thresholds, overconsumption, loan due reminders, timed reminders."""
    #初始化提醒服务，启动后台监控线程
    def __init__(self, user: User, ui_callback=None):
        self.user = user
        self.ui_callback = ui_callback  # function to call for UI actions (message display)
        self._timer = None
        self._stop_event = threading.Event()
        self._warned_urgent = False  # ← 先初始化所有属性
        self._check_interval = 10  # seconds for demo; in real app, could be 60+
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._warned_low = False
        
    #后台线程的主循环，定期检查各种提醒条件
    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_thresholds()
                self.check_loans()
            except Exception as e:
                print("ReminderService loop error:", e)
            self._stop_event.wait(self._check_interval)

    #停止提醒服务线程
    def stop(self):
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
    #检查余额是否低于预警/紧急阈值
    def check_thresholds(self):
        bal = self.user.get_balance()
        warn = float(self.user.settings.get('threshold_warn', 3000.0))
        urgent = float(self.user.settings.get('threshold_urgent', 1000.0))

        # ✅ 紧急阈值（仅提醒一次）
        if bal <= urgent:
            if not self._warned_urgent:
                self._notify('urgent', f'余额已低于紧急阈值：{bal:.2f}')
                self._warned_urgent = True
            self._warned_low = True
            return

        # ✅ 预警阈值（仅提醒一次）
        if bal <= warn:
            if not self._warned_low:
                self._notify('warn', f'余额已低于预警阈值：{bal:.2f}')
                self._warned_low = True
            self._warned_urgent = False
            return

        # ✅ 回到安全区，全部重置
        self._warned_low = False
        self._warned_urgent = False

    #检查新增记录是否为过度消费类别
    def check_overconsumption(self, record: Record):
        if record.category in self.user.overcats:
            self._notify('over', f'检测到可能的过度消费：{record.category}，金额：{record.amount:.2f}')
    # 检查是否有到期的未还款借款
    def check_loans(self):
        today = datetime.date.today()
        for l in self.user.loans:
            if l.due_date and not l.repaid:
                try:
                    dd = datetime.datetime.fromisoformat(l.due_date).date()
                    if dd <= today:
                        self._notify('loan', f'借款到期：{l.name} 金额 {l.amount:.2f} 应还日期 {l.due_date}')
                except Exception:
                    pass
    #设置每日提醒（当前仅存储设置，未完全实现）
    def schedule_daily_reminder(self, time_hhmm: str, enabled: bool):
        # For simplicity, we will not schedule a strict daily system notification here.
        # Instead, we store setting and UIController may use it to show a dialog
        self.user.settings['reminder_enabled'] = bool(enabled)
        self.user.settings['reminder_time'] = time_hhmm
        self.user.storage.update_settings(self.user.settings)

    #发送提醒消息到UI回调函数
    def _notify(self, kind: str, message: str):
        print(f'[Reminder] {kind}: {message}')
        if self.ui_callback:
            try:
                self.ui_callback(kind, message)
            except Exception as e:
                print("UI callback failed:", e)


# ----------------------------- GUI Layer ------------------------------------

class UIController:
    """Tkinter-based GUI controller that connects User, Statistics, ReminderService."""
    #初始化主界面控制器
    def __init__(self, root: tk.Tk, user: User):
        self.root = root
        self.user = user
        self.stats = Statistics(user)
        self.reminder = ReminderService(user, ui_callback=self.on_reminder)
        self.root.title('记账本系统 - Expense Manager')
        self.create_widgets()
        self.refresh_records_list()

    def create_widgets(self):
        '''
        功能: 创建所有界面组件，包括：

        顶部：余额显示和控制按钮

        中部：记录列表和分类饼图

        右侧：过度消费类别列表

        底部：状态栏
        '''
        # Top frame: Balance display and controls
        top = ttk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        self.balance_var = tk.StringVar()
       
        ttk.Label(top, text='当前余额:').pack(side=tk.LEFT)
        self.balance_label = ttk.Label(top, textvariable=self.balance_var, font=('Arial', 14, 'bold'))
        self.balance_label.pack(side=tk.LEFT, padx=(6, 12))

        self.update_balance_var()

        ttk.Button(top, text='设置余额', command=self.on_set_balance).pack(side=tk.LEFT)
        ttk.Button(top, text='阈值设置', command=self.on_set_thresholds).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text='导入/导出', command=self.on_import_export).pack(side=tk.LEFT, padx=6)

        # Middle: Records list and controls
        mid = ttk.Frame(self.root)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        left = ttk.Frame(mid)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Controls
        btn_frame = ttk.Frame(left)
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(btn_frame, text='添加记录', command=self.on_add_record).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='编辑选中', command=self.on_edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text='删除选中', command=self.on_delete_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text='添加借款', command=self.on_add_loan).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text='借款管理', command=self.on_manage_loans).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text='统计视图', command=self.on_show_stats).pack(side=tk.LEFT, padx=6)

        # Record list
        self.tree = ttk.Treeview(left, columns=('amount', 'kind', 'category', 'time', 'note'), show='headings', selectmode='browse')
        for col, title in [('amount', '金额'), ('kind', '类型'), ('category', '类别'), ('time', '时间'), ('note', '备注')]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=100, anchor='center')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        # Right: simple category pie visualization and overconsumption list
        right = ttk.Frame(mid, width=240)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(right, text='分类占比(示意)').pack(anchor='nw')
        self.canvas = tk.Canvas(right, width=220, height=220, bg='white', highlightthickness=1, highlightbackground='#ccc')
        self.canvas.pack(pady=6)
        ttk.Label(right, text='被标注为过度消费的类别:').pack(anchor='nw', pady=(6, 0))
        self.over_listbox = tk.Listbox(right, height=6)
        self.over_listbox.pack(fill=tk.X)
        ttk.Button(right, text='添加过度类别', command=self.on_add_overcat).pack(fill=tk.X, pady=4)
        ttk.Button(right, text='移除选中过度', command=self.on_remove_overcat).pack(fill=tk.X)

        # Bottom: status bar
        bottom = ttk.Frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.status_var).pack(side=tk.LEFT, padx=6)
        self.update_status("就绪")

        # Bind double click to edit
        self.tree.bind('<Double-1>', lambda e: self.on_edit_selected())

    #更新状态栏文本
    def update_status(self, msg: str):
        self.status_var.set(f'状态: {msg}')

    # 更新余额显示，并根据阈值改变颜色
    def update_balance_var(self):
        bal = self.user.get_balance()
        self.balance_var.set(f'{bal:.2f}')
        # update color based on thresholds
        warn = float(self.user.settings.get('threshold_warn', 3000.0))
        urgent = float(self.user.settings.get('threshold_urgent', 1000.0))
        if bal <= urgent:
            color = '#ff4d4f'  # red
        elif bal <= warn:
            color = '#faad14'  # orange
        else:
            color = '#52c41a'  # green
        self.balance_label.configure(foreground=color)

    # 刷新记录列表显示，按时间倒序排列
    def refresh_records_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in sorted(self.user.records, key=lambda x: x.timestamp, reverse=True):
            self.tree.insert('', tk.END, iid=r.id, values=(f'{r.amount:.2f}', r.kind, r.category, r.timestamp, r.note))
        self.update_balance_var()
        self.update_overconsumption_list()
        self.draw_pie_chart()

    # 更新过度消费类别列表显示
    def update_overconsumption_list(self):
        self.over_listbox.delete(0, tk.END)
        for c in sorted(self.user.overcats):
            self.over_listbox.insert(tk.END, c)

    #在画布上绘制分类支出饼图
    def draw_pie_chart(self):
        # Very simple pie-like visualization using canvas: draw arcs proportional to expense by category
        self.canvas.delete('all')
        breakdown = self.stats.category_breakdown()
        total = sum(v for k, v in breakdown.items() if k != 'Income')
        if total <= 0:
            self.canvas.create_text(110, 110, text='无支出数据', fill='#999')
            return
        start = 0
        colors = ['#ff9999', '#99ccff', '#ffd699', '#c2f0c2', '#dcb2ff', '#f7b2d9', '#b3e6ff']
        i = 0
        for k, v in breakdown.items():
            if k == 'Income':
                continue
            extent = int(360 * (v / total))
            color = colors[i % len(colors)]
            self.canvas.create_arc(10, 10, 210, 210, start=start, extent=extent, fill=color, outline='white')
            # label position: compute midpoint angle
            mid = (start + start + extent) / 2
            import math
            angle = math.radians(mid)
            cx, cy = 110 + 70 * math.cos(angle), 110 + 70 * math.sin(angle)
            self.canvas.create_text(cx, cy, text=k, font=('Arial', 8))
            start += extent
            i += 1
    def on_backup_data(self):
        """备份数据菜单项"""
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON备份文件', '*.json')],
            title='选择备份文件保存位置'
        )
        if path:
            try:
                backup_path = self.user.create_backup(path)
                messagebox.showinfo('备份成功', f'数据已备份到: {backup_path}')
            except Exception as e:
                messagebox.showerror('备份失败', str(e))
    
    def on_restore_data(self):
        """恢复数据菜单项"""
        if not messagebox.askyesno('确认恢复', '恢复将覆盖当前所有数据，确定继续吗？'):
            return
        
        path = filedialog.askopenfilename(
            filetypes=[('JSON备份文件', '*.json')],
            title='选择备份文件'
        )
        if path:
            try:
                if self.user.restore_from_backup(path):
                    self.refresh_records_list()
                    messagebox.showinfo('恢复成功', '数据恢复完成')
            except Exception as e:
                messagebox.showerror('恢复失败', str(e))
    # ---------------- GUI actions -----------------------------------------
    def on_add_record(self):
        dlg = RecordDialog(self.root, title='添加记录')
        if dlg.result:
            kind, amount, category, timestamp, note = dlg.result
            rec = self.user.add_record(amount=amount, kind=kind, category=category, timestamp=timestamp, note=note)
            self.reminder.check_overconsumption(rec)
            self.refresh_records_list()
            self.update_status('添加记录成功')

    def on_edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选择一条记录')
            return
        rid = sel[0]
        rec = next((r for r in self.user.records if r.id == rid), None)
        if not rec:
            messagebox.showerror('错误', '未找到记录')
            return
        dlg = RecordDialog(self.root, title='编辑记录', record=rec)
        if dlg.result:
            kind, amount, category, timestamp, note = dlg.result
            self.user.update_record(rid, amount=amount, kind=kind, category=category, timestamp=timestamp, note=note)
            self.refresh_records_list()
            self.update_status('更新记录成功')

    def on_delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选择一条记录')
            return
        rid = sel[0]
        if messagebox.askyesno('确认', '确定删除该记录吗？'):
            if self.user.delete_record(rid):
                self.refresh_records_list()
                self.update_status('删除记录成功')
            else:
                messagebox.showerror('错误', '删除失败')

    def on_set_balance(self):
        cur = float(self.user.settings.get('initial_balance', 0.0))
        val = simpledialog.askfloat('设置初始余额', '请输入初始余额：', initialvalue=cur, minvalue=-1e9, maxvalue=1e12)
        if val is not None:
            self.user.set_initial_balance(val)
            self.refresh_records_list()
            self.update_status('初始余额已更新')

    def on_set_thresholds(self):
        warn = float(self.user.settings.get('threshold_warn', 3000.0))
        urgent = float(self.user.settings.get('threshold_urgent', 1000.0))
        win = tk.Toplevel(self.root)
        win.title('阈值设置')
        ttk.Label(win, text='预警阈值:').grid(row=0, column=0, sticky='e', padx=6, pady=6)
        e1 = ttk.Entry(win)
        e1.insert(0, str(warn))
        e1.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(win, text='紧急阈值:').grid(row=1, column=0, sticky='e', padx=6, pady=6)
        e2 = ttk.Entry(win)
        e2.insert(0, str(urgent))
        e2.grid(row=1, column=1, padx=6, pady=6)
        def on_ok():
            try:
                w = float(e1.get())
                u = float(e2.get())
                self.user.set_thresholds(w, u)
                self.refresh_records_list()
                win.destroy()
            except Exception:
                messagebox.showerror('错误', '请输入有效数字')
        ttk.Button(win, text='保存', command=on_ok).grid(row=2, column=0, columnspan=2, pady=8)

    def on_add_overcat(self):
        cat = simpledialog.askstring('添加过度消费类别', '请输入类别名称：')
        if cat:
            self.user.add_overconsumption_category(cat.strip())
            self.refresh_records_list()
            self.update_status('已添加过度消费类别')

    def on_remove_overcat(self):
        sel = self.over_listbox.curselection()
        if not sel:
            messagebox.showinfo('提示', '请先选择一个类别')
            return
        idx = sel[0]
        cat = self.over_listbox.get(idx)
        self.user.remove_overconsumption_category(cat)
        self.refresh_records_list()
        self.update_status('已移除过度消费类别')

    def on_add_loan(self):
        dlg = LoanDialog(self.root, title='添加借款记录')
        if dlg.result:
            name, amount, loan_date, due_date, note = dlg.result
            self.user.add_loan(name=name, amount=amount, loan_date=loan_date, due_date=due_date, note=note)
            self.refresh_records_list()
            self.update_status('添加借款成功')

    def on_manage_loans(self):
        win = LoanManager(self.root, user=self.user, refresh_callback=self.refresh_records_list)
        win.show()

    def on_show_stats(self):
        win = StatsWindow(self.root, stats=self.stats)
        win.show()

    def on_import_export(self):
        # Offer user to import or export data JSON
        if messagebox.askyesno('导出', '导出数据到 JSON 文件？（点击否可选择导入）'):
            path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
            if path:
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        data = {
                            'records': [r.to_dict() for r in self.user.records],
                            'loans': [l.to_dict() for l in self.user.loans],
                            'settings': self.user.settings,
                            'overconsumption_categories': list(self.user.overcats)
                        }
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        messagebox.showinfo('导出成功', f'已导出到 {path}')
                except Exception as e:
                    messagebox.showerror('错误', str(e))
        else:
            path = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
            if path:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # basic merge/replace behavior
                        if 'records' in data:
                            self.user.records = [Record.from_dict(d) for d in data['records']]
                        if 'loans' in data:
                            self.user.loans = [LoanRecord.from_dict(d) for d in data['loans']]
                        if 'settings' in data:
                            self.user.settings.update(data['settings'])
                        if 'overconsumption_categories' in data:
                            self.user.overcats = set(data['overconsumption_categories'])
                        self.user.storage.set_records(self.user.records)
                        self.user.storage.set_loans(self.user.loans)
                        self.user.storage.update_settings(self.user.settings)
                        self.user.storage.set_overconsumption_categories(list(self.user.overcats))
                        self.refresh_records_list()
                        messagebox.showinfo('导入成功', '已成功导入数据')
                except Exception as e:
                    messagebox.showerror('错误', str(e))

    def on_reminder(self, kind: str, message: str):
        # Called from ReminderService thread; ensure we call tkinter safely
        def show():
            if kind == 'urgent':
                messagebox.showwarning('紧急提醒', message)
            elif kind == 'warn':
                messagebox.showinfo('余额预警', message)
            elif kind == 'over':
                messagebox.showinfo('过度消费提示', message)
            elif kind == 'loan':
                messagebox.showinfo('借款提醒', message)
            self.update_status(message)
            self.update_balance_var()
        try:
            self.root.after(0, show)
        except Exception as e:
            print("Failed to schedule UI reminder:", e)

    def on_close(self):
        if messagebox.askyesno('退出', '确定要退出吗？'):
            self.reminder.stop()
            self.root.destroy()


# ---------------- Dialogs and helper windows -------------------------------

class RecordDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None, record: Optional[Record] = None):
        self.record = record
        self.result = None
        super().__init__(parent, title=title)

    def body(self, master):
        ttk.Label(master, text='类型:').grid(row=0, column=0, sticky='e')
        self.kind_var = tk.StringVar(value=self.record.kind if self.record else 'expense')
        ttk.Radiobutton(master, text='支出', variable=self.kind_var, value='expense').grid(row=0, column=1)
        ttk.Radiobutton(master, text='收入', variable=self.kind_var, value='income').grid(row=0, column=2)

        ttk.Label(master, text='金额:').grid(row=1, column=0, sticky='e')
        self.amount_e = ttk.Entry(master)
        self.amount_e.grid(row=1, column=1, columnspan=2, sticky='we')
        ttk.Label(master, text='类别:').grid(row=2, column=0, sticky='e')
        self.cat_e = ttk.Entry(master)
        self.cat_e.grid(row=2, column=1, columnspan=2, sticky='we')
        ttk.Label(master, text='时间(ISO):').grid(row=3, column=0, sticky='e')
        self.time_e = ttk.Entry(master)
        self.time_e.grid(row=3, column=1, columnspan=2, sticky='we')
        ttk.Label(master, text='备注:').grid(row=4, column=0, sticky='ne')
        self.note_e = tk.Text(master, height=4, width=30)
        self.note_e.grid(row=4, column=1, columnspan=2, sticky='we')

        # populate if editing
        if self.record:
            self.amount_e.insert(0, str(self.record.amount))
            self.cat_e.insert(0, self.record.category)
            self.time_e.insert(0, self.record.timestamp)
            self.note_e.insert('1.0', self.record.note)

        return self.amount_e  # initial focus

    def validate(self):
        try:
            a = float(self.amount_e.get())
            if a < 0:
                raise ValueError('金额应为非负数')
            if not self.cat_e.get().strip():
                raise ValueError('类别不能为空')
            return True
        except Exception as e:
            messagebox.showerror('输入错误', str(e))
            return False

    def apply(self):
        kind = self.kind_var.get()
        amount = float(self.amount_e.get())
        category = self.cat_e.get().strip()
        timestamp = self.time_e.get().strip() or now_iso()
        note = self.note_e.get('1.0', tk.END).strip()
        self.result = (kind, amount, category, timestamp, note)


class LoanDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None):
        self.result = None
        super().__init__(parent, title=title)

    def body(self, master):
        ttk.Label(master, text='借款人:').grid(row=0, column=0, sticky='e')
        self.name_e = ttk.Entry(master); self.name_e.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(master, text='金额:').grid(row=1, column=0, sticky='e')
        self.amount_e = ttk.Entry(master); self.amount_e.grid(row=1, column=1, padx=6, pady=6)
        ttk.Label(master, text='借出日期(ISO 可选):').grid(row=2, column=0, sticky='e')
        self.loan_e = ttk.Entry(master); self.loan_e.grid(row=2, column=1, padx=6, pady=6)
        ttk.Label(master, text='到期日期(ISO 可选):').grid(row=3, column=0, sticky='e')
        self.due_e = ttk.Entry(master); self.due_e.grid(row=3, column=1, padx=6, pady=6)
        ttk.Label(master, text='备注:').grid(row=4, column=0, sticky='ne')
        self.note_e = tk.Text(master, height=4, width=30); self.note_e.grid(row=4, column=1, padx=6, pady=6)
        return self.name_e

    def validate(self):
        try:
            a = float(self.amount_e.get())
            return True
        except Exception as e:
            messagebox.showerror('输入错误', '请输入有效金额')
            return False

    def apply(self):
        name = self.name_e.get().strip()
        amount = float(self.amount_e.get())
        loan_date = self.loan_e.get().strip() or now_iso()
        due_date = self.due_e.get().strip() or None
        note = self.note_e.get('1.0', tk.END).strip()
        self.result = (name, amount, loan_date, due_date, note)


class LoanManager:
    def __init__(self, parent, user: User, refresh_callback=None):
        self.user = user
        self.refresh_callback = refresh_callback
        self.win = tk.Toplevel(parent)
        self.win.title('借款管理')
        self.frame = ttk.Frame(self.win); self.frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree = ttk.Treeview(self.frame, columns=('name', 'amount', 'loan_date', 'due_date', 'repaid'), show='headings')
        for c, t in [('name', '借款人'), ('amount', '金额'), ('loan_date', '借出日期'), ('due_date', '到期'), ('repaid', '已还')]:
            self.tree.heading(c, text=t); self.tree.column(c, width=100)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview); vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        ctl = ttk.Frame(self.win); ctl.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(ctl, text='标记已还', command=self.mark_repaid).pack(side=tk.LEFT)
        ttk.Button(ctl, text='删除', command=self.delete_loan).pack(side=tk.LEFT, padx=6)
        ttk.Button(ctl, text='关闭', command=self.win.destroy).pack(side=tk.RIGHT)
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for l in self.user.loans:
            self.tree.insert('', tk.END, iid=l.id, values=(l.name, f'{l.amount:.2f}', l.loan_date or '', l.due_date or '', '是' if l.repaid else '否'))

    def mark_repaid(self):
        sel = self.tree.selection()
        if not sel: return
        lid = sel[0]
        if self.user.mark_loan_repaid(lid):
            self.refresh()
            if self.refresh_callback: self.refresh_callback()

    def delete_loan(self):
        sel = self.tree.selection()
        if not sel: return
        lid = sel[0]
        if messagebox.askyesno('确认', '确定删除该借款记录吗？'):
            if self.user.delete_loan(lid):
                self.refresh()
                if self.refresh_callback: self.refresh_callback()

    def show(self):
        self.win.transient(self.win.master)
        self.win.grab_set()
        self.win.wait_window()

#统计数据显示窗口
class StatsWindow:
    def __init__(self, parent, stats: Statistics):
        self.stats = stats
        self.win = tk.Toplevel(parent)
        self.win.title('统计视图')
        self.frame = ttk.Frame(self.win); self.frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        ttk.Label(self.frame, text='月份对比 (最近 6 个月)').pack(anchor='w')
        self.tbl = ttk.Treeview(self.frame, columns=('month', 'income', 'expense'), show='headings')
        for c, t in [('month', '月份'), ('income', '收入'), ('expense', '支出')]:
            self.tbl.heading(c, text=t); self.tbl.column(c, width=100)
        self.tbl.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.frame, text='关闭', command=self.win.destroy).pack(pady=6)
        self.refresh()

    def refresh(self):
        for i in self.tbl.get_children():
            self.tbl.delete(i)
        for m, inc, exp in self.stats.monthly_series(6):
            self.tbl.insert('', tk.END, values=(m, f'{inc:.2f}', f'{exp:.2f}'))

    def show(self):
        self.win.transient(self.win.master)
        self.win.grab_set()
        self.win.wait_window()


# ----------------------------- Main -----------------------------------------

def main():
    storage = Storage(path='data.json')
    user = User(storage=storage)

    root = tk.Tk()
    app = UIController(root, user=user)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.geometry('900x600')
    root.mainloop()

if __name__ == '__main__':
    main()
