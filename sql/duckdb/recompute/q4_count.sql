-- SOURCE_FILE: normal_test.sql
-- SOURCE_OBJECT: fourth summary INSERT...SELECT (tombstone)
-- METHOD: recompute
-- QUERY_FORM: count
-- TRANSFORMATIONS: removed INSERT target; wrapped in COUNT/MINMAX/export; CTE recompute chain; dialect adaptation
SELECT COUNT(*) AS cnt FROM (
SELECT
    t.head_id, t.period_id, t.period_id_dd, t.period_id_qty,
    t.bill_type, t.business_type, t.node_type,
    t.invoice_category, t.invoice_type_name, t.company_code,
    t.cfs_salesperson_code, t.cfs_salesperson_name,
    t.cfs_region_id, t.cfs_region_code, t.cfs_region_en_name,
    t.cfs_repoffice_code, t.cfs_repoffice_en_name,
    t.region_code, t.region_cn_name, t.region_en_name,
    t.repoffice_code, t.repoffice_cn_name, t.repoffice_en_name,
    t.country_code, t.country_cn_name, t.country_en_name,
    t.bg_code, t.bg_cn_name, t.bg_en_name,
    t.customer_code, t.customer_name, t.customer_group_name,
    t.contract_number, t.customer_pono,
    t.hw_contract_bussource_code, t.project_number, t.project_name,
    t.invoice_id, t.invoice_no, t.operator_application_id,
    t.milestone_name, t.currency_code,
    t.usd_total_amount, t.rmb_total_amount, t.total_amount,
    t.creation_date, t.submit_date, t.applicant_time,
    t.con_mi_qty, t.over_due_days,
    t.current_handler_code, t.current_handler_name,
    t.currentrole, t.todo_billing_id,
    t.source_code, t.details_flag, t.billing_status,
    t.rtd_last_update_date, true AS logical_is_deleted,
    t.src_cdc_event_date, t.src_cdc_last_update_date,
    t._hoodie_event_time, t.frame_contract_no,
    t.reason_code, t.sub_reason_code, t.remarks, t.responsible_person,
    t.estimated_resolution_time, t.cfs_status, t.sla,
    t.reason_cn_name, t.reason_en_name,
    t.sub_reason_cn_name, t.sub_reason_en_name,
    t.responsible_person_id, t.responsible_person_code,
    t.tax_invoice_date, t.payment_unit_number
FROM s000_dwt_hws_iao.dwd_billing_in_transit_t_05 t
INNER JOIN (
    SELECT head_id, SUM(CASE WHEN logical_is_deleted IS TRUE THEN 0 ELSE 1 END) AS del_flag
    FROM s000_dwt_hws_iao.dwd_billing_in_transit_dtl_t_05
    GROUP BY head_id
) t1 ON REPLACE(REPLACE(t.head_id, 'false', ''), 'true', '') = t1.head_id
WHERE t1.del_flag = 0
) AS q;
