#!/usr/bin/env python3
"""
Deterministic data generator for the Job 5 streaming-query benchmark.
Reads table definitions from data_model.py, generates CSV files for
static tables (unsliced) and dynamic tables (1% slices).

SOURCE_FILE: create_table_ddl.sql, create_primary_key_ddl.sql, job5表信息.xlsx
"""

import csv
import hashlib
import math
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_model import TABLES, static_tables, dynamic_tables, output_tables
from config import Config


# ── Helpers ──

def make_rng(seed, *extra):
    h = hashlib.sha256(f"{seed}|{'|'.join(str(e) for e in extra)}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], 'big'))


def ts(rng, start=datetime(2022, 3, 1), end=datetime(2025, 6, 1)):
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=rng.random() * delta)


def ts_str(dt):
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def dec(rng, lo=0.0, hi=100000.0, prec=2):
    return round(rng.uniform(lo, hi), prec)


def pick(rng, choices):
    return rng.choice(choices)


def nullable(rng, val, null_prob=0.3):
    return val if rng.random() > null_prob else None


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow([c.name for c in columns])
        for row in rows:
            w.writerow(row)


def dict_to_row(fqn, d):
    """Convert a {col_name: value} dict to a list in the correct column order."""
    tdef = TABLES[fqn]
    return [d.get(c.name, "") for c in tdef.columns]


class IDPool:
    def __init__(self, start=1):
        self._next = start

    def take(self, n=1):
        ids = list(range(self._next, self._next + n))
        self._next += n
        return ids

    @property
    def next_id(self):
        return self._next


# ── Static table generators ──

def gen_node_define(rng, n):
    rows = []
    for i in range(1, n + 1):
        rows.append([
            i, f"NODE_{i:03d}", f"node_{i}", f"节点{i}",
            pick(rng, [1, 2, 3]), i * 10, "Y",
            None, 1, ts_str(ts(rng)), 1, ts_str(ts(rng)),
            ts_str(ts(rng)), False, str(int(datetime.now().timestamp() * 1000)),
        ])
    return rows


def gen_currencies(rng, n):
    codes = ["USD", "CNY", "EUR", "GBP", "JPY", "KRW", "AUD", "CAD",
             "CHF", "SGD", "HKD", "TWD", "THB", "MYR", "IDR", "PHP",
             "VND", "INR", "BRL", "RUB"]
    rows = []
    for i in range(1, n + 1):
        code = codes[i % len(codes)]
        usd_rate = round(rng.uniform(0.001, 10.0), 6)
        rmb_rate = round(usd_rate * rng.uniform(6.5, 7.5), 6)
        rows.append([
            f"CUR_{i:06d}", str(i), code,
            ts_str(ts(rng, datetime(2020, 1, 1), datetime(2025, 1, 1))),
            usd_rate, rmb_rate,
            str(int(datetime.now().timestamp() * 1000)),
        ])
    return rows


def gen_customer(rng, n):
    rows = []
    groups = [f"GRP_{g:03d}" for g in range(1, 51)]
    for i in range(1, n + 1):
        grp = pick(rng, groups)
        rows.append([
            i, f"CUST_{i:08d}", f"Customer_{i}",
            grp, f"Group_{grp}",
            str(int(datetime.now().timestamp() * 1000)),
        ])
    return rows


def gen_invtype(rng, n):
    categories = ["增值税专用发票", "增值税普通发票", "形式发票", "商业发票", "其他"]
    rows = []
    for i in range(1, n + 1):
        cat = pick(rng, categories)
        rows.append([
            i, i * 10, f"CAT_{i:03d}", cat, f"Type_{i}",
            str(int(datetime.now().timestamp() * 1000)),
        ])
    rows.append([
        -999, -9990, "NONE", "", "N/A",
        str(int(datetime.now().timestamp() * 1000)),
    ])
    return rows


def gen_salesperson_region(rng, n):
    source_codes = ["业务补录", "原始表中已有的账套"]
    regions = [f"REG_{r:02d}" for r in range(1, 11)]
    rows = []
    sp_id_set = set()
    for i in range(1, n + 1):
        sp_id = (i // 2) + 1
        sp_id_set.add(sp_id)
        sc = source_codes[i % 2]
        reg = pick(rng, regions)
        rows.append([
            f"SP_{i:06d}", sp_id, i * 100,
            f"SP_CODE_{sp_id:06d}", f"Salesperson_{sp_id}",
            reg, f"Region_{reg}", f"RO_{reg}", f"RepOffice_{reg}",
            f"CC_{reg}", f"Country_{reg}", f"CS_{reg}",
            f"UNIT_{(i % 50) + 1:04d}" if sc == "原始表中已有的账套" else None,
            None, f"CC_{i:03d}", f"国家{i}", f"Country_{i}",
            f"RO_{i:03d}", f"办事处{i}", f"RepOffice_{i}",
            reg, f"大区{reg}", f"Region_{reg}",
            None, None, None,
            str(int(datetime.now().timestamp() * 1000)), sc,
        ])
    return rows


def gen_job_status(rng):
    old_ts = datetime(2020, 1, 1)
    return [[
        "5", "job5", "billing_in_transit",
        ts_str(old_ts), ts_str(old_ts), ts_str(old_ts),
        ts_str(old_ts), False, ts_str(old_ts), ts_str(old_ts),
        str(int(datetime.now().timestamp() * 1000)),
    ]]


# ── Dynamic table generators ──

class DataContext:
    """Shared state for consistent cross-table generation."""
    def __init__(self, cfg, rng, dataset_tag="base"):
        self.cfg = cfg
        self.rng = rng
        self.dataset_tag = dataset_tag
        sf = cfg.scale_factor

        # Lookup pools from static tables
        self.n_currencies = max(1, int(181 * sf))
        self.currency_ids = list(range(1, self.n_currencies + 1))
        self.n_customers_static = max(1, int(1066915 * sf))
        self.n_salesperson_region = max(1, int(2939 * sf))
        self.salesperson_ids = list(set((i // 2) + 1 for i in range(1, self.n_salesperson_region + 1)))
        self.n_node_define = max(1, int(13 * sf))
        self.node_define_ids = list(range(1, self.n_node_define + 1))
        self.n_invtype = max(1, int(1019 * sf))

        # Dynamic table row targets
        self.n_company = max(1, int(394 * sf))
        self.n_cinv = max(10, int(2194000 * sf))
        self.n_payment_unit = max(10, int(8189259 * sf))
        self.n_invoice_info = max(10, int(13300036 * sf))
        self.n_app_inst = max(10, int(1278414 * sf))
        self.n_application = max(5, int(166000 * sf))
        self.n_route = max(5, int(6695 * sf))
        self.n_task = max(5, int(393768 * sf))
        self.n_message = max(5, int(35551 * sf))
        self.n_user = max(5, int(1412649 * sf))
        self.n_contract = max(5, int(5447025 * sf))

        pk_offset = 0 if dataset_tag == "base" else 500_000_000

        # ID pools with disjoint ranges for base vs extra
        self.company_ids = IDPool(1 + pk_offset)
        self.cinv_ids = IDPool(1 + pk_offset)
        self.pu_ids = IDPool(1 + pk_offset)
        self.inv_ids = IDPool(1 + pk_offset)
        self.inst_ids = IDPool(1 + pk_offset)
        self.app_ids = IDPool(1 + pk_offset)
        self.route_ids = IDPool(1 + pk_offset)
        self.task_ids = IDPool(1 + pk_offset)
        self.msg_ids = IDPool(1 + pk_offset)
        self.user_ids = IDPool(1 + pk_offset)
        self.contract_ids = IDPool(1 + pk_offset)

        # Cross-table link pools built during generation
        self.company_codes = []   # (company_id, company_code, unit_code)
        self.app_code_map = {}    # operator_application_id -> application_code
        self.app_status_map = {}  # operator_application_id -> status
        self.app_contract_map = {}
        self.app_wf_map = {}      # operator_application_id -> work_flow_id
        self.inst_app_map = {}    # application_inst_id -> operator_application_id
        self.inst_pu_map = {}     # application_inst_id -> payment_unit_id
        self.contract_id_list = []
        self.user_id_list = []
        self.pu_contract_map = {}
        self.task_proc_map = {}   # proc_inst_id -> task_id
        self.route_node_map = {}  # route_id -> node_define_id


def gen_company(ctx):
    FQN = "s000_cqrs_cfs.cfs_cfg_company_t"
    rng = ctx.rng
    n = ctx.n_company
    ids = ctx.company_ids.take(n)
    rows = []
    for i, cid in enumerate(ids):
        unit_code = f"UNIT_{(i % 50) + 1:04d}"
        code = f"COMP_{cid:06d}"
        ctx.company_codes.append((cid, code, unit_code))
        cur_id = pick(rng, ctx.currency_ids)
        rows.append(dict_to_row(FQN, {
            "company_id": cid, "company_code": code, "company_name": f"Company_{cid}",
            "company_name_zh": f"公司{cid}", "enable_flag": "Y",
            "use_flag": 1, "currency_id": cur_id, "exchange_type": 1, "version": 1,
            "created_by": 1, "creation_date": ts_str(ts(rng)),
            "last_update_date": ts_str(ts(rng)), "last_updated_by": 1,
            "cdc_last_update_date": ts_str(ts(rng)),
            "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_contract(ctx):
    FQN = "s000_dwt_hws_iao.cfs_comm_contract_t"
    rng = ctx.rng
    n = ctx.n_contract
    ids = ctx.contract_ids.take(n)
    ctx.contract_id_list = list(ids)
    bsource_codes = ["NON_OEM"] * 9 + ["OEM"]
    rows = []
    for cid in ids:
        sp_id = pick(rng, ctx.salesperson_ids)
        comp = pick(rng, ctx.company_codes) if ctx.company_codes else (1, "COMP_1", "UNIT_0001")
        rows.append(dict_to_row(FQN, {
            "contract_id": cid, "salesperson_id": sp_id, "company_id": comp[0],
            "contract_number": f"CON_{cid:08d}", "contract_flag": pick(rng, [1, 2]),
            "customer_pono": f"PO_{cid}", "bg_code": "BG01",
            "bg_cn_name": "消费者BG", "bg_en_name": "Consumer BG",
            "hw_contract_bussource_code": pick(rng, bsource_codes),
            "project_number": f"PRJ_{cid:06d}", "project_name": f"Project_{cid}",
            "customer_id": pick(rng, range(1, ctx.n_customers_static + 1)),
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
            "frame_contract_no": f"FC_{cid:06d}" if rng.random() > 0.7 else "",
        }))
    return rows


def gen_application(ctx):
    FQN = "s000_cqrs_cfs.cfs_opt_application_t"
    rng = ctx.rng
    n = ctx.n_application
    ids = ctx.app_ids.take(n)
    rows = []
    statuses = [30] * 4 + [40] * 3 + [50] * 3
    for app_id in ids:
        status = pick(rng, statuses)
        code = f"APP_{app_id:08d}"
        con_id = pick(rng, ctx.contract_id_list) if ctx.contract_id_list else 1
        sp_id = pick(rng, ctx.salesperson_ids)
        comp = pick(rng, ctx.company_codes) if ctx.company_codes else (1, "COMP_1", "UNIT_0001")
        cur_id = pick(rng, ctx.currency_ids)
        cust_id = rng.randint(1, ctx.n_customers_static)
        wf_id = rng.randint(1, max(1, ctx.n_task))
        creation = ts(rng, datetime(2022, 6, 1), datetime(2025, 5, 1))
        app_time = creation + timedelta(hours=rng.randint(1, 48))
        cdc = creation + timedelta(minutes=rng.randint(-30, 30))

        ctx.app_code_map[app_id] = code
        ctx.app_status_map[app_id] = status
        ctx.app_contract_map[app_id] = con_id
        ctx.app_wf_map[app_id] = wf_id

        rows.append(dict_to_row(FQN, {
            "operator_application_id": app_id, "application_code": code,
            "contract_id": con_id, "salesperson_id": sp_id, "company_id": comp[0],
            "customer_id": cust_id, "application_type": 1, "currency_id": cur_id,
            "total_amount": dec(rng, 100, 500000, 3), "status": status,
            "applicant_time": ts_str(app_time),
            "approve_time": ts_str(app_time) if status >= 30 else "",
            "version": 1, "creation_date": ts_str(creation), "created_by": 1,
            "last_update_date": ts_str(creation), "last_updated_by": 1,
            "work_flow_id": wf_id,
            "cdc_last_update_date": ts_str(cdc), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_application_inst(ctx):
    FQN = "s000_cqrs_cfs.cfs_opt_application_inst_t"
    rng = ctx.rng
    n = ctx.n_app_inst
    ids = ctx.inst_ids.take(n)
    app_id_list = list(ctx.app_code_map.keys())
    rows = []
    for inst_id in ids:
        app_id = pick(rng, app_id_list) if app_id_list else 1
        con_id = ctx.app_contract_map.get(app_id, 1)
        pu_id = rng.randint(1, max(1, ctx.n_payment_unit)) if rng.random() > 0.1 else None
        creation = ts(rng, datetime(2022, 6, 1), datetime(2025, 5, 1))
        cdc = creation + timedelta(minutes=rng.randint(-30, 30))

        ctx.inst_app_map[inst_id] = app_id
        ctx.inst_pu_map[inst_id] = pu_id

        rows.append(dict_to_row(FQN, {
            "application_inst_id": inst_id, "operator_application_id": app_id,
            "contract_id": con_id, "payment_unit_id": pu_id if pu_id else "",
            "total_amount": dec(rng, 100, 500000, 3),
            "contract_amount": dec(rng, 100, 500000, 3),
            "unbilled_amount": dec(rng, 0, 100000, 3),
            "billed_amount": dec(rng, 0, 100000, 3),
            "invoiced_amount": dec(rng, 0, 100000, 3),
            "version": 1, "creation_date": ts_str(creation), "created_by": 1,
            "last_update_date": ts_str(creation), "last_updated_by": 1,
            "cdc_last_update_date": ts_str(cdc), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_customer_invoice(ctx):
    rng = ctx.rng
    n = ctx.n_cinv
    ids = ctx.cinv_ids.take(n)
    app_codes = list(ctx.app_code_map.values())
    statuses = [3, 4, 5, 10, 20, 30, 40, 50]
    rows = []
    for cid in ids:
        status = pick(rng, statuses)
        code = pick(rng, app_codes) if app_codes else f"APP_{cid:08d}"
        comp = pick(rng, ctx.company_codes) if ctx.company_codes else (1, "COMP_1", "UNIT_0001")
        sp_id = pick(rng, ctx.salesperson_ids)
        cur_id = pick(rng, ctx.currency_ids)
        approve_dt = ts(rng) if status >= 30 else None
        send_dt = ts(rng) if status >= 40 else None
        office_dt = ts(rng) if rng.random() > 0.4 else None
        cust_recv_dt = ts(rng) if rng.random() > 0.4 else None
        tax_inv_dt = ts(rng) if rng.random() > 0.3 else None
        creation = ts(rng, datetime(2022, 1, 1), datetime(2025, 6, 1))
        cdc = creation + timedelta(minutes=rng.randint(-30, 30))

        rows.append(dict_to_row("s000_cqrs_cfs.cfs_cinv_customer_invoice_t", {
            "customer_invoice_id": cid, "invoice_no": f"INV_{cid:010d}",
            "accounting_tax_flag": pick(rng, [0, 1]),
            "company_id": comp[0], "salesperson_id": sp_id, "status": status,
            "approve_date": ts_str(approve_dt), "send_date": ts_str(send_dt),
            "customer_receive_date": ts_str(cust_recv_dt),
            "total_amount": dec(rng, 100, 500000, 4), "currency_id": cur_id,
            "customer_id": rng.randint(1, ctx.n_customers_static),
            "tax_invoice_date": ts_str(tax_inv_dt),
            "office_receive_date": ts_str(office_dt),
            "creation_date": ts_str(creation), "created_by": 1,
            "last_update_date": ts_str(creation), "application_code": code,
            "cdc_last_update_date": ts_str(cdc), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_invoice_info(ctx):
    rng = ctx.rng
    n = ctx.n_invoice_info
    ids = ctx.inv_ids.take(n)
    app_codes = list(ctx.app_code_map.values())
    statuses_query = [30, 40]
    statuses_other = [10, 20, 50, 60]
    rows = []
    for iid in ids:
        status = pick(rng, statuses_query + statuses_other)
        code = pick(rng, app_codes) if app_codes else f"APP_{iid:08d}"
        comp = pick(rng, ctx.company_codes) if ctx.company_codes else (1, "COMP_1", "UNIT_0001")
        sp_id = pick(rng, ctx.salesperson_ids)
        cur_id = pick(rng, ctx.currency_ids)
        approve_dt = ts(rng) if status >= 30 else None
        send_dt = ts(rng) if status >= 40 else None
        creation = ts(rng, datetime(2022, 1, 1), datetime(2025, 6, 1))
        cdc = creation + timedelta(minutes=rng.randint(-30, 30))

        rows.append(dict_to_row("s000_cqrs_cfs.cfs_inv_invoice_info_t", {
            "invoice_id": iid, "salesperson_id": sp_id, "company_id": comp[0],
            "customer_id": rng.randint(1, ctx.n_customers_static),
            "status": status, "currency_id": cur_id,
            "net_amount": dec(rng, 100, 500000, 3),
            "total_amount": dec(rng, 100, 500000, 3),
            "approve_date": ts_str(approve_dt), "send_date": ts_str(send_dt),
            "version": 1, "creation_date": ts_str(creation),
            "last_update_date": ts_str(creation), "application_code": code,
            "tax_invoice_no": f"TAXINV_{iid:010d}" if rng.random() > 0.3 else "",
            "cdc_last_update_date": ts_str(cdc), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_payment_unit(ctx):
    rng = ctx.rng
    n = ctx.n_payment_unit
    ids = ctx.pu_ids.take(n)
    rows = []
    for pid in ids:
        sp_id = pick(rng, ctx.salesperson_ids)
        comp = pick(rng, ctx.company_codes) if ctx.company_codes else (1, "COMP_1", "UNIT_0001")
        cur_id = pick(rng, ctx.currency_ids)
        con_id = pick(rng, ctx.contract_id_list) if ctx.contract_id_list else 1
        cust_id = rng.randint(1, ctx.n_customers_static)
        creation = ts(rng, datetime(2022, 1, 1), datetime(2025, 6, 1))
        cdc = creation + timedelta(minutes=rng.randint(-30, 30))

        rows.append(dict_to_row("s000_cqrs_cfs.cfs_con_payment_unit_t", {
            "payment_unit_id": pid, "salesperson_id": sp_id, "company_id": comp[0],
            "customer_id": cust_id, "currency_id": cur_id,
            "contract_id": con_id, "contract_number": f"CON_{con_id:08d}",
            "payment_unit_number": f"PU_{pid:08d}", "payment_unit_name": f"PayUnit_{pid}",
            "version": 1, "created_by": 1,
            "creation_date": ts_str(creation), "last_update_date": ts_str(creation),
            "cdc_last_update_date": ts_str(cdc), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_route(ctx):
    FQN = "s000_cqrs_cfs.cfs_proc_route_t"
    rng = ctx.rng
    n = ctx.n_route
    ids = ctx.route_ids.take(n)
    rows = []
    for rid in ids:
        nid = pick(rng, ctx.node_define_ids)
        ctx.route_node_map[rid] = nid
        creation = ts(rng)
        rows.append(dict_to_row(FQN, {
            "route_id": rid, "proc_define_id": rng.randint(1, 100),
            "node_define_id": nid, "route_seq": rng.randint(1, 10),
            "created_by": 1, "creation_date": ts_str(creation),
            "last_updated_by": 1, "last_update_date": ts_str(creation),
            "cdc_last_update_date": ts_str(creation), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_task(ctx):
    FQN = "s000_cqrs_cfs.cfs_proc_task_t"
    rng = ctx.rng
    n = ctx.n_task
    ids = ctx.task_ids.take(n)
    route_ids = list(ctx.route_node_map.keys()) if ctx.route_node_map else [1]
    rows = []
    for tid in ids:
        proc_id = rng.randint(1, max(1, ctx.n_task * 2))
        rid = pick(rng, route_ids)
        ctx.task_proc_map[proc_id] = tid
        creation = ts(rng)
        rows.append(dict_to_row(FQN, {
            "task_id": tid, "proc_inst_id": proc_id, "route_id": rid,
            "handler_id": rng.randint(1, max(1, ctx.n_user)),
            "created_by": 1, "creation_date": ts_str(creation),
            "last_updated_by": 1, "last_update_date": ts_str(creation),
            "cdc_last_update_date": ts_str(creation), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


def gen_message(ctx):
    FQN = "s000_cqrs_cfs.tpl_fd_message_t"
    rng = ctx.rng
    n = ctx.n_message
    ids = ctx.msg_ids.take(n)
    rows = []
    special_added = False
    for mid in ids:
        creation = ts(rng)
        if not special_added:
            rows.append(dict_to_row(FQN, {
                "message_id": mid,
                "message_key": "cfs.html.label.role.operatorInvoiceSender",
                "message": "开票寄送员", "language": "zh_CN",
                "created_by": 1, "creation_date": ts_str(creation),
                "last_updated_by": 1, "last_update_date": ts_str(creation),
                "app_name": "cfs", "ispublic": 1,
                "cdc_last_update_date": ts_str(creation), "logical_is_deleted": False,
                "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
            }))
            special_added = True
        else:
            rows.append(dict_to_row(FQN, {
                "message_id": mid, "message_key": f"msg.key.{mid}",
                "message": f"Message_{mid}",
                "language": pick(rng, ["zh_CN", "en_US"]),
                "created_by": 1, "creation_date": ts_str(creation),
                "last_updated_by": 1, "last_update_date": ts_str(creation),
                "app_name": pick(rng, ["cfs", "tpl", "sys"]),
                "ispublic": pick(rng, [0, 1]),
                "cdc_last_update_date": ts_str(creation), "logical_is_deleted": False,
                "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
            }))
    return rows


def gen_user(ctx):
    FQN = "s000_cqrs_cfs.tpl_user_t"
    rng = ctx.rng
    n = ctx.n_user
    ids = ctx.user_ids.take(n)
    ctx.user_id_list = list(ids)
    rows = []
    for uid in ids:
        creation = ts(rng)
        rows.append(dict_to_row(FQN, {
            "fname": f"First_{uid}", "lname": f"Last_{uid}",
            "employee_number": f"EMP_{uid:06d}",
            "w3_account": f"w3_{uid}", "type": "E",
            "email": f"user{uid}@test.com", "user_id": uid,
            "created_by": 1, "creation_date": ts_str(creation),
            "last_updated_by": 1, "last_update_date": ts_str(creation),
            "hr_employee_id": uid, "employee_name_eng": f"Employee_{uid}",
            "start_date": ts_str(creation), "enable_flag": "Y",
            "cdc_last_update_date": ts_str(creation), "logical_is_deleted": False,
            "_hoodie_event_time": str(int(datetime.now().timestamp() * 1000)),
        }))
    return rows


# ── Slice-splitting logic ──

def split_into_slices(rows, total_slices):
    n = len(rows)
    slices = []
    for s in range(total_slices):
        start = (n * s) // total_slices
        end = (n * (s + 1)) // total_slices
        slices.append(rows[start:end])
    return slices


def generate_delete_keys(rows, pk_indices):
    return [[row[i] for i in pk_indices] for row in rows]


# ── Main generation orchestrator ──

def generate_all(cfg: Config):
    rng_base = make_rng(cfg.seed, "base")
    print(f"Generating data with seed={cfg.seed}, scale={cfg.scale_factor}")

    data_dir = cfg.data_dir  # scale-specific: data/scale_X/
    static_dir = cfg.static_dir  # shared: data/static/
    total_slices = cfg.total_slices

    # ── Static tables (shared across scales, only generate if missing) ──
    static_gen = {
        "s000_cqrs_cfs.cfs_proc_node_define_t": lambda r: gen_node_define(r, 13),
        "s000_dwt_hws_iao.cfs_comm_currencies_t": lambda r: gen_currencies(r, 181),
        "s000_dwt_hws_iao.cfs_comm_customer_t": lambda r: gen_customer(r, 1066915),
        "s000_dwt_hws_iao.cfs_comm_invtype_t": lambda r: gen_invtype(r, 1019),
        "s000_dwt_hws_iao.cfs_salesperson_region_t": lambda r: gen_salesperson_region(r, 2939),
        "s000_dwt_hws_iao.dwd_job_status_t_05": lambda r: gen_job_status(r),
    }

    all_static_exist = all(
        (static_dir / TABLES[fqn].csv_name).exists() for fqn in static_gen
    )
    if all_static_exist:
        print("Static tables already exist, skipping.")
    else:
        print("Generating static tables...")
        for fqn, gen_fn in static_gen.items():
            tdef = TABLES[fqn]
            rows = gen_fn(make_rng(cfg.seed, "static", fqn))
            path = static_dir / tdef.csv_name
            write_csv(path, rows, tdef.columns)
            print(f"  {fqn}: {len(rows)} rows -> {path}")

    # ── Dynamic tables: base ──
    print("Generating dynamic base data...")
    ctx_base = DataContext(cfg, make_rng(cfg.seed, "base"), "base")
    _generate_dynamic_set(cfg, ctx_base, data_dir, "base", total_slices)

    # ── Dynamic tables: extra ──
    print("Generating dynamic extra data...")
    ctx_extra = DataContext(cfg, make_rng(cfg.seed, "extra"), "extra")
    _generate_dynamic_set(cfg, ctx_extra, data_dir, "extra", total_slices)

    # Write table manifest
    manifest_dir = data_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    with open(manifest_dir / "tables.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["schema", "table", "is_static", "is_output", "target_rows", "pk_columns"])
        for fqn, tdef in sorted(TABLES.items()):
            w.writerow([tdef.schema, tdef.table, tdef.is_static, tdef.is_output,
                         tdef.target_rows, ";".join(tdef.pk_columns)])

    print("Data generation complete.")


def _generate_dynamic_set(cfg, ctx, data_dir, tag, total_slices):
    dyn_gen_order = [
        ("s000_cqrs_cfs.cfs_cfg_company_t", gen_company),
        ("s000_dwt_hws_iao.cfs_comm_contract_t", gen_contract),
        ("s000_cqrs_cfs.cfs_opt_application_t", gen_application),
        ("s000_cqrs_cfs.cfs_opt_application_inst_t", gen_application_inst),
        ("s000_cqrs_cfs.cfs_cinv_customer_invoice_t", gen_customer_invoice),
        ("s000_cqrs_cfs.cfs_inv_invoice_info_t", gen_invoice_info),
        ("s000_cqrs_cfs.cfs_con_payment_unit_t", gen_payment_unit),
        ("s000_cqrs_cfs.cfs_proc_route_t", gen_route),
        ("s000_cqrs_cfs.cfs_proc_task_t", gen_task),
        ("s000_cqrs_cfs.tpl_fd_message_t", gen_message),
        ("s000_cqrs_cfs.tpl_user_t", gen_user),
    ]

    def _generate_streaming(ctx, gen_fn, fqn, tdef, data_dir, tag,
                             total_slices, pk_indices, dk_cols, slice_manifest):
        """Generate a large table directly into slice files to avoid holding all rows in memory."""
        rows = gen_fn(ctx)
        total_rows = len(rows)
        BATCH = 100_000
        # Open all slice files at once and distribute rows
        slice_files = {}
        dk_files = {}
        for s_idx in range(total_slices):
            pct = f"pct_{s_idx + 1:03d}"
            csv_path = data_dir / "dynamic" / tag / pct / tdef.csv_name
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            f = open(csv_path, "w", newline="", encoding="utf-8")
            w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            w.writerow([c.name for c in tdef.columns])
            slice_files[s_idx] = (f, w, 0)
            dk_path = data_dir / "delete_keys" / tag / pct / tdef.csv_name
            dk_path.parent.mkdir(parents=True, exist_ok=True)
            df = open(dk_path, "w", newline="", encoding="utf-8")
            dw = csv.writer(df, quoting=csv.QUOTE_MINIMAL)
            dw.writerow([c.name for c in dk_cols])
            dk_files[s_idx] = (df, dw)

        for row_idx, row in enumerate(rows):
            s_idx = (row_idx * total_slices) // total_rows
            if s_idx >= total_slices:
                s_idx = total_slices - 1
            f, w, cnt = slice_files[s_idx]
            w.writerow(row)
            slice_files[s_idx] = (f, w, cnt + 1)
            df, dw = dk_files[s_idx]
            dw.writerow([row[i] for i in pk_indices])

        for s_idx in range(total_slices):
            f, w, cnt = slice_files[s_idx]
            f.close()
            df, dw = dk_files[s_idx]
            df.close()
            pct = f"pct_{s_idx + 1:03d}"
            slice_manifest.append((tdef.csv_name, pct, cnt))

        del rows
        return total_rows

    STREAM_THRESHOLD = 500_000

    slice_manifest = []
    for fqn, gen_fn in dyn_gen_order:
        tdef = TABLES[fqn]
        pk_indices = [i for i, c in enumerate(tdef.columns) if c.name in tdef.pk_columns]
        dk_cols = [tdef.columns[i] for i in pk_indices]

        n_target = getattr(ctx, {
            "s000_cqrs_cfs.cfs_cfg_company_t": "n_company",
            "s000_dwt_hws_iao.cfs_comm_contract_t": "n_contract",
            "s000_cqrs_cfs.cfs_opt_application_t": "n_application",
            "s000_cqrs_cfs.cfs_opt_application_inst_t": "n_app_inst",
            "s000_cqrs_cfs.cfs_cinv_customer_invoice_t": "n_cinv",
            "s000_cqrs_cfs.cfs_inv_invoice_info_t": "n_invoice_info",
            "s000_cqrs_cfs.cfs_con_payment_unit_t": "n_payment_unit",
            "s000_cqrs_cfs.cfs_proc_route_t": "n_route",
            "s000_cqrs_cfs.cfs_proc_task_t": "n_task",
            "s000_cqrs_cfs.tpl_fd_message_t": "n_message",
            "s000_cqrs_cfs.tpl_user_t": "n_user",
        }.get(fqn, "n_company"), 0)

        if n_target > STREAM_THRESHOLD:
            total_rows = _generate_streaming(ctx, gen_fn, fqn, tdef, data_dir, tag,
                                              total_slices, pk_indices, dk_cols, slice_manifest)
        else:
            rows = gen_fn(ctx)
            total_rows = len(rows)
            for s_idx in range(total_slices):
                start = (total_rows * s_idx) // total_slices
                end = (total_rows * (s_idx + 1)) // total_slices
                s_rows = rows[start:end]
                pct = f"pct_{s_idx + 1:03d}"
                write_csv(data_dir / "dynamic" / tag / pct / tdef.csv_name, s_rows, tdef.columns)
                dk_rows = generate_delete_keys(s_rows, pk_indices)
                write_csv(data_dir / "delete_keys" / tag / pct / tdef.csv_name, dk_rows, dk_cols)
                slice_manifest.append((tdef.csv_name, pct, len(s_rows)))
            del rows

        import gc; gc.collect()
        print(f"  {fqn}: {total_rows} rows -> {total_slices} slices ({tag})", flush=True)

    manifest_dir = data_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    with open(manifest_dir / f"{tag}_slices.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "slice", "rows"])
        for name, pct, count in slice_manifest:
            w.writerow([name, pct, count])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Job 5 benchmark data")
    parser.add_argument("--seed", type=int, default=20260715)
    parser.add_argument("--scale", type=float, default=0.01)
    parser.add_argument("--csv-slice-percent", type=int, default=1)
    args = parser.parse_args()

    cfg = Config(
        seed=args.seed,
        scale_factor=args.scale,
        csv_slice_percent=args.csv_slice_percent,
    )
    generate_all(cfg)
