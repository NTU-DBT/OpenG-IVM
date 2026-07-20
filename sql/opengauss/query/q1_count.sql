-- SOURCE_FILE: normal_test.sql + create_matview.sql
-- SOURCE_OBJECT: first detail query from maintained materialized tables
-- METHOD: logical_views | ivm
-- QUERY_FORM: count
-- TRANSFORMATIONS: removed INSERT target; reads incremental materialized views; dialect adaptation
SELECT COUNT(*) AS cnt FROM (
SELECT
    fact_t.id,
    fact_t.head_id,
    fact_t.period_id,
    fact_t.period_id_dd,
    fact_t.period_id_qty,
    fact_t.business_id,
    fact_t.bill_type,
    fact_t.business_type,
    fact_t.node_type,
    fact_t.invoice_type_id,
    type_t.invoice_category,
    type_t.invoice_type_name,
    fact_t.salesperson_id,
    fact_t.company_id,
    comp_t.company_code,
    comp_t.company_name,
    COALESCE(sprt1.salesperson_code, sprt2.salesperson_code) AS cfs_salesperson_code,
    COALESCE(sprt1.salesperson_name, sprt2.salesperson_name) AS cfs_salesperson_name,
    COALESCE(sprt1.cfs_region_id, sprt2.cfs_region_id) AS cfs_region_id,
    COALESCE(sprt1.cfs_region_code, sprt2.cfs_region_code) AS cfs_region_code,
    COALESCE(sprt1.cfs_region_en_name, sprt2.cfs_region_en_name) AS cfs_region_en_name,
    COALESCE(sprt1.cfs_repoffice_code, sprt2.cfs_repoffice_code) AS cfs_repoffice_code,
    COALESCE(sprt1.cfs_repoffice_en_name, sprt2.cfs_repoffice_en_name) AS cfs_repoffice_en_name,
    COALESCE(sprt1.region_code, sprt2.region_code) AS region_code,
    COALESCE(sprt1.region_cn_name, sprt2.region_cn_name) AS region_cn_name,
    COALESCE(sprt1.region_en_name, sprt2.region_en_name) AS region_en_name,
    COALESCE(sprt1.repoffice_code, sprt2.repoffice_code) AS repoffice_code,
    COALESCE(sprt1.repoffice_cn_name, sprt2.repoffice_cn_name) AS repoffice_cn_name,
    COALESCE(sprt1.repoffice_en_name, sprt2.repoffice_en_name) AS repoffice_en_name,
    COALESCE(sprt1.country_code, sprt2.country_code) AS country_code,
    COALESCE(sprt1.country_cn_name, sprt2.country_cn_name) AS country_cn_name,
    COALESCE(sprt1.country_en_name, sprt2.country_en_name) AS country_en_name,
    cont_t.bg_code, cont_t.bg_cn_name, cont_t.bg_en_name,
    fact_t.customer_id,
    cust_t.customer_code, cust_t.customer_name, cust_t.customer_group_name,
    fact_t.contract_id,
    cont_t.contract_number, cont_t.customer_pono,
    cont_t.hw_contract_bussource_code, cont_t.project_number, cont_t.project_name,
    fact_t.invoice_id, fact_t.invoice_no,
    fact_t.operator_application_id, fact_t.application_code,
    fact_t.milestone_name, fact_t.currency_id,
    curr_t.from_currency_code,
    curr_t.usd_rate * fact_t.total_amount AS usd_total_amount,
    curr_t.rmb_rate * fact_t.total_amount AS rmb_total_amount,
    fact_t.total_amount, fact_t.creation_date,
    fact_t.submit_date, fact_t.applicant_time,
    1 AS con_mi_qty,
    fact_t.current_handler_id,
    user_t.lname AS current_handler_code,
    user_t.lname AS current_handler_name,
    fact_t.currentrole,
    fact_t.todo_billing_id, fact_t.payment_unit_id,
    fact_t.source_code, fact_t.details_flag, fact_t.billing_status,
    CURRENT_TIMESTAMP AS rtd_last_update_date,
    fact_t.logical_is_deleted,
    CURRENT_TIMESTAMP AS src_cdc_event_date,
    CURRENT_TIMESTAMP AS src_cdc_last_update_date,
    CAST((extract(epoch from current_timestamp) * 1000) AS VARCHAR) AS _hoodie_event_time,
    cont_t.frame_contract_no,
    CAST(NULL AS VARCHAR) AS reason_code,
    CAST(NULL AS VARCHAR) AS sub_reason_code,
    CAST(NULL AS VARCHAR) AS remarks,
    CAST(NULL AS VARCHAR) AS responsible_person,
    CAST(NULL AS TIMESTAMP) AS estimated_resolution_time,
    CAST(NULL AS VARCHAR) AS cfs_status,
    CAST(NULL AS BIGINT) AS sla,
    CAST(NULL AS VARCHAR) AS reason_cn_name,
    CAST(NULL AS VARCHAR) AS reason_en_name,
    CAST(NULL AS VARCHAR) AS sub_reason_cn_name,
    CAST(NULL AS VARCHAR) AS sub_reason_en_name,
    CAST(NULL AS BIGINT) AS responsible_person_id,
    CAST(NULL AS VARCHAR) AS responsible_person_code,
    fact_t.tax_invoice_date,
    fact_t.payment_unit_number
FROM fact_t_mv AS fact_t
LEFT JOIN s000_dwt_hws_iao.cfs_comm_invtype_t AS type_t ON fact_t.invoice_type_id = type_t.invoice_type_id
LEFT JOIN s000_cqrs_cfs.cfs_cfg_company_t AS comp_t ON fact_t.company_id = comp_t.company_id
LEFT JOIN s000_dwt_hws_iao.cfs_salesperson_region_t AS sprt1
    ON fact_t.salesperson_id = sprt1.salesperson_id AND sprt1.source_code = '业务补录'
LEFT JOIN s000_dwt_hws_iao.cfs_salesperson_region_t AS sprt2
    ON fact_t.salesperson_id = sprt2.salesperson_id
    AND comp_t.company_code = sprt2.unit_code AND sprt2.source_code = '原始表中已有的账套'
LEFT JOIN s000_dwt_hws_iao.cfs_comm_customer_t AS cust_t ON fact_t.customer_id = cust_t.customer_id
INNER JOIN s000_dwt_hws_iao.cfs_comm_contract_t AS cont_t ON fact_t.contract_id = cont_t.contract_id
LEFT JOIN s000_dwt_hws_iao.cfs_comm_currencies_t AS curr_t ON CAST(fact_t.currency_id AS VARCHAR) = curr_t.from_currency_id
LEFT JOIN s000_cqrs_cfs.tpl_user_t AS user_t ON fact_t.current_handler_id = user_t.user_id
LEFT JOIN s000_dwt_hws_iao.dwd_job_status_t_05 f ON (1 = 1)
WHERE
    (cont_t.hw_contract_bussource_code <> 'OEM' OR cont_t.hw_contract_bussource_code IS NULL)
    AND (sprt1.salesperson_id IS NOT NULL OR sprt2.salesperson_id IS NOT NULL)
    AND fact_t.cdc_last_update_date >= f.job_last_start_date - INTERVAL '30 MINUTE'
) AS q;
