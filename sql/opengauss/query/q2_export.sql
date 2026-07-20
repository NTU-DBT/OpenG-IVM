-- SOURCE_FILE: normal_test.sql + create_matview.sql
-- SOURCE_OBJECT: second detail tombstone from maintained materialized tables
-- METHOD: logical_views | ivm
-- QUERY_FORM: export
-- TRANSFORMATIONS: removed INSERT target; reads incremental materialized views; dialect adaptation
COPY (
SELECT
    fact_t.id, fact_t.head_id, fact_t.period_id, fact_t.period_id_dd,
    fact_t.period_id_qty, fact_t.business_id, fact_t.bill_type, fact_t.business_type,
    fact_t.node_type, fact_t.invoice_type_id, fact_t.invoice_category, fact_t.invoice_type_name,
    fact_t.salesperson_id, fact_t.company_id, fact_t.company_code, fact_t.company_name,
    fact_t.cfs_salesperson_code, fact_t.cfs_salesperson_name,
    fact_t.cfs_region_id, fact_t.cfs_region_code, fact_t.cfs_region_en_name,
    fact_t.cfs_repoffice_code, fact_t.cfs_repoffice_en_name,
    fact_t.region_code, fact_t.region_cn_name, fact_t.region_en_name,
    fact_t.repoffice_code, fact_t.repoffice_cn_name, fact_t.repoffice_en_name,
    fact_t.country_code, fact_t.country_cn_name, fact_t.country_en_name,
    fact_t.bg_code, fact_t.bg_cn_name, fact_t.bg_en_name,
    fact_t.customer_id, fact_t.customer_code, fact_t.customer_name, fact_t.customer_group_name,
    fact_t.contract_id, fact_t.contract_number, fact_t.customer_pono,
    fact_t.hw_contract_bussource_code, fact_t.project_number, fact_t.project_name,
    fact_t.invoice_id, fact_t.invoice_no, fact_t.operator_application_id,
    fact_t.application_code, fact_t.milestone_name,
    fact_t.currency_id, fact_t.currency_code,
    fact_t.usd_total_amount, fact_t.rmb_total_amount, fact_t.total_amount,
    fact_t.creation_date, fact_t.submit_date, fact_t.applicant_time,
    fact_t.con_mi_qty, fact_t.current_handler_id,
    fact_t.current_handler_code, fact_t.current_handler_name,
    fact_t.currentrole, fact_t.todo_billing_id, fact_t.payment_unit_id,
    fact_t.source_code, fact_t.details_flag, fact_t.billing_status,
    CURRENT_TIMESTAMP AS rtd_last_update_date,
    true AS logical_is_deleted,
    fact_t.src_cdc_event_date, fact_t.src_cdc_last_update_date,
    CAST((extract(epoch from current_timestamp) * 1000) AS VARCHAR) AS _hoodie_event_time,
    fact_t.frame_contract_no,
    CAST(NULL AS VARCHAR) AS reason_code, CAST(NULL AS VARCHAR) AS sub_reason_code,
    CAST(NULL AS VARCHAR) AS remarks, CAST(NULL AS VARCHAR) AS responsible_person,
    CAST(NULL AS TIMESTAMP) AS estimated_resolution_time,
    CAST(NULL AS VARCHAR) AS cfs_status, CAST(NULL AS BIGINT) AS sla,
    CAST(NULL AS VARCHAR) AS reason_cn_name, CAST(NULL AS VARCHAR) AS reason_en_name,
    CAST(NULL AS VARCHAR) AS sub_reason_cn_name, CAST(NULL AS VARCHAR) AS sub_reason_en_name,
    CAST(NULL AS BIGINT) AS responsible_person_id, CAST(NULL AS VARCHAR) AS responsible_person_code,
    fact_t.tax_invoice_date, fact_t.payment_unit_number
FROM s000_dwt_hws_iao.dwd_billing_in_transit_dtl_t_05 fact_t
WHERE
    (fact_t.node_type IN ('待审批')
        AND NOT EXISTS (SELECT 1 FROM approval_temp_mv oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
    OR (fact_t.node_type IN ('待寄送')
        AND NOT EXISTS (SELECT 1 FROM send_temp_mv oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
    OR (fact_t.node_type IN ('待签返')
        AND NOT EXISTS (SELECT 1 FROM countersign_temp_mv oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
) TO '__WORK_DIR__/current/output/q2.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
