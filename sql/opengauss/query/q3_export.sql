-- SOURCE_FILE: normal_test.sql + create_matview.sql
-- SOURCE_OBJECT: third summary from maintained materialized tables
-- METHOD: logical_views | ivm
-- QUERY_FORM: export
-- TRANSFORMATIONS: removed INSERT target; reads incremental materialized views; dialect adaptation
COPY (
SELECT
    t.head_id || CAST(t.logical_is_deleted AS VARCHAR) AS head_id,
    MAX(t.period_id), MAX(t.period_id_dd), MAX(t.period_id_qty),
    MAX(t.bill_type), MAX(t.business_type), MAX(t.node_type),
    MAX(t.invoice_category), MAX(t.invoice_type_name), MAX(t.company_code),
    MAX(t.cfs_salesperson_code), MAX(t.cfs_salesperson_name),
    MAX(t.cfs_region_id), MAX(t.cfs_region_code), MAX(t.cfs_region_en_name),
    MAX(t.cfs_repoffice_code), MAX(t.cfs_repoffice_en_name),
    MAX(t.region_code), MAX(t.region_cn_name), MAX(t.region_en_name),
    MAX(t.repoffice_code), MAX(t.repoffice_cn_name), MAX(t.repoffice_en_name),
    MAX(t.country_code), MAX(t.country_cn_name), MAX(t.country_en_name),
    MAX(t.bg_code), MAX(t.bg_cn_name), MAX(t.bg_en_name),
    MAX(t.customer_code), MAX(t.customer_name), MAX(t.customer_group_name),
    SUBSTR(string_agg(t.contract_number, ','), 1, 1000),
    SUBSTR(string_agg(t.customer_pono, ','), 1, 1000),
    SUBSTR(string_agg(t.hw_contract_bussource_code, ','), 1, 1000),
    SUBSTR(string_agg(t.project_number, ','), 1, 1000),
    SUBSTR(string_agg(t.project_name, ','), 1, 1000),
    MAX(t.invoice_id), MAX(t.invoice_no), MAX(t.operator_application_id),
    MAX(t.milestone_name), MAX(t.currency_code),
    SUM(t.usd_total_amount), SUM(t.rmb_total_amount), SUM(t.total_amount),
    MAX(t.creation_date), MAX(t.submit_date), MAX(t.applicant_time),
    SUM(t.con_mi_qty),
    CAST(NULL AS BIGINT) AS over_due_days,
    MAX(t.current_handler_code), MAX(t.current_handler_name),
    MAX(t.currentrole), MAX(t.todo_billing_id),
    MAX(t.source_code), MAX(t.details_flag),
    SUBSTR(string_agg(t.billing_status, ','), 1, 1000),
    MAX(t.rtd_last_update_date), t.logical_is_deleted,
    MAX(t.src_cdc_event_date), MAX(t.src_cdc_last_update_date),
    MAX(t._hoodie_event_time),
    SUBSTR(string_agg(t.frame_contract_no, ','), 1, 1000),
    MAX(t.reason_code), MAX(t.sub_reason_code),
    MAX(t.remarks), MAX(t.responsible_person),
    MAX(t.estimated_resolution_time), MAX(t.cfs_status),
    MAX(t.sla), MAX(t.reason_cn_name), MAX(t.reason_en_name),
    MAX(t.sub_reason_cn_name), MAX(t.sub_reason_en_name),
    MAX(t.responsible_person_id), MAX(t.responsible_person_code),
    MAX(t.tax_invoice_date),
    SUBSTR(string_agg(DISTINCT t.payment_unit_number, ',' ORDER BY t.payment_unit_number), 1, 1000) AS payment_unit_number
FROM s000_dwt_hws_iao.dwd_billing_in_transit_dtl_t_05 t
INNER JOIN (
    SELECT fact_t.id
    FROM fact_t_mv AS fact_t
    LEFT JOIN s000_dwt_hws_iao.dwd_job_status_t_05 f ON (1 = 1)
    WHERE fact_t.cdc_last_update_date >= f.job_last_start_date - INTERVAL '30 MINUTE'
) scp ON t.id = scp.id
GROUP BY t.head_id, t.logical_is_deleted
) TO '__WORK_DIR__/current/output/q3.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
