-- SOURCE_FILE: normal_test.sql
-- SOURCE_OBJECT: first detail INSERT...SELECT
-- METHOD: recompute
-- QUERY_FORM: export
-- TRANSFORMATIONS: removed INSERT target; wrapped in COUNT/MINMAX/export; CTE recompute chain; dialect adaptation
COPY (
WITH tmp_zx_send_countersign_t AS (
    SELECT
        ccci.application_code,
        ccci.approve_date,
        ccci.status,
        ccci.invoice_no,
        ccci.send_date,
        ccci.office_receive_date,
        ccci.customer_receive_date,
        ccci.tax_invoice_date,
        '1' as type
    FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t ccci
    WHERE ccci.status >= 3
    UNION ALL
    SELECT
        cici.application_code,
        cici.approve_date,
        cici.status,
        cici.tax_invoice_no AS invoice_no,
        cici.send_date,
        NULL AS office_receive_date,
        NULL AS customer_receive_date,
        NULL AS tax_invoice_date,
        '2' as type
    FROM s000_cqrs_cfs.cfs_inv_invoice_info_t cici
    WHERE cici.status IN (30, 40)
),
apt AS (
    SELECT application_code, MAX(tax_invoice_date) AS tax_invoice_date
    FROM tmp_zx_send_countersign_t
    WHERE type = '1'
    GROUP BY application_code
),
tmp_cfs_opt_application_inst_t AS (
    SELECT
        opii.application_inst_id,
        oa.operator_application_id,
        oa.application_code,
        oa.salesperson_id,
        oa.company_id,
        oa.customer_id,
        opii.contract_id,
        oa.currency_id,
        oa.total_amount,
        oa.creation_date,
        oa.applicant_time,
        oa.logical_is_deleted,
        GREATEST(oa.cdc_last_update_date, opii.cdc_last_update_date) AS cdc_last_update_date,
        oa.work_flow_id,
        oa.application_type,
        oa.status,
        GREATEST(CAST(oa.logical_is_deleted AS INTEGER), CAST(opii.logical_is_deleted AS INTEGER))::BOOLEAN AS logical_is_deleted_del,
        opii.payment_unit_id,
        pu.payment_unit_number,
        apt_t.tax_invoice_date
    FROM s000_cqrs_cfs.cfs_opt_application_t oa
    JOIN s000_cqrs_cfs.cfs_opt_application_inst_t opii
        ON oa.operator_application_id = opii.operator_application_id
    LEFT JOIN s000_cqrs_cfs.cfs_con_payment_unit_t pu
        ON opii.payment_unit_id = pu.payment_unit_id
    LEFT JOIN apt apt_t
        ON oa.application_code = apt_t.application_code
    WHERE oa.application_type = 1
      AND oa.status IN (30, 40, 50)
      AND oa.creation_date > TIMESTAMP '2022-01-01 00:00:00'
),
approval_temp AS (
    SELECT
        oa.application_inst_id AS id,
        CAST(oa.operator_application_id AS VARCHAR) AS head_id,
        oa.application_code,
        CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
        oa.operator_application_id AS business_id,
        '税票' AS bill_type, '正项' AS business_type, '待审批' AS node_type,
        -999 AS invoice_type_id,
        oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
        CAST(NULL AS BIGINT) AS invoice_id, CAST(NULL AS VARCHAR) AS invoice_no,
        oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
        oa.currency_id, oa.total_amount, oa.creation_date,
        oa.applicant_time AS submit_date, oa.applicant_time,
        CAST(NULL AS BIGINT) AS current_handler_id,
        node.node_define_name_cn AS currentrole,
        CAST(NULL AS BIGINT) AS todo_billing_id,
        CAST(NULL AS BIGINT) AS payment_unit_id,
        CAST(NULL AS VARCHAR) AS source_code,
        CAST(NULL AS VARCHAR) AS details_flag,
        CAST(NULL AS VARCHAR) AS billing_status,
        oa.logical_is_deleted,
        oa.cdc_last_update_date,
        oa.logical_is_deleted_del,
        oa.tax_invoice_date,
        oa.payment_unit_number
    FROM tmp_cfs_opt_application_inst_t oa
    LEFT JOIN s000_cqrs_cfs.cfs_proc_task_t task ON oa.work_flow_id = task.proc_inst_id
    LEFT JOIN s000_cqrs_cfs.cfs_proc_route_t route ON task.route_id = route.route_id
    LEFT JOIN s000_cqrs_cfs.cfs_proc_node_define_t node ON route.node_define_id = node.node_define_id
    WHERE oa.status = 30
),
send_temp AS (
    SELECT
        oa.application_inst_id AS id,
        CAST(oa.operator_application_id AS VARCHAR) AS head_id,
        oa.application_code,
        CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
        oa.operator_application_id AS business_id,
        '税票' AS bill_type, '正项' AS business_type, '待寄送' AS node_type,
        -999 AS invoice_type_id,
        oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
        CAST(NULL AS BIGINT) AS invoice_id, CAST(NULL AS VARCHAR) AS invoice_no,
        oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
        oa.currency_id, oa.total_amount, oa.creation_date,
        temp.approve_date AS submit_date, oa.applicant_time,
        CAST(NULL AS BIGINT) AS current_handler_id,
        mes.message AS currentrole,
        CAST(NULL AS BIGINT) AS todo_billing_id,
        CAST(NULL AS BIGINT) AS payment_unit_id,
        CAST(NULL AS VARCHAR) AS source_code,
        CAST(NULL AS VARCHAR) AS details_flag,
        CAST(NULL AS VARCHAR) AS billing_status,
        oa.logical_is_deleted,
        oa.cdc_last_update_date,
        oa.logical_is_deleted_del,
        oa.tax_invoice_date,
        oa.payment_unit_number
    FROM tmp_cfs_opt_application_inst_t oa
    JOIN (
        SELECT t.application_code, MAX(t.approve_date) AS approve_date
        FROM tmp_zx_send_countersign_t t WHERE t.status = 30
        GROUP BY t.application_code
    ) temp ON temp.application_code = oa.application_code
    LEFT JOIN s000_cqrs_cfs.tpl_fd_message_t mes
        ON mes.app_name = 'cfs' AND mes.language = 'zh_CN'
        AND mes.message_key = 'cfs.html.label.role.operatorInvoiceSender'
    WHERE oa.status = 40
),
countersign_temp AS (
    SELECT
        oa.application_inst_id AS id,
        CAST(oa.operator_application_id AS VARCHAR) AS head_id,
        oa.application_code,
        CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
        CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
        oa.operator_application_id AS business_id,
        '税票' AS bill_type, '正项' AS business_type, '待签返' AS node_type,
        -999 AS invoice_type_id,
        oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
        CAST(NULL AS BIGINT) AS invoice_id, tic.invoice_no,
        oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
        oa.currency_id, oa.total_amount, oa.creation_date,
        tic.send_date AS submit_date, oa.applicant_time,
        CAST(NULL AS BIGINT) AS current_handler_id,
        '结束' AS currentrole,
        CAST(NULL AS BIGINT) AS todo_billing_id,
        CAST(NULL AS BIGINT) AS payment_unit_id,
        CAST(NULL AS VARCHAR) AS source_code,
        CAST(NULL AS VARCHAR) AS details_flag,
        CAST(NULL AS VARCHAR) AS billing_status,
        oa.logical_is_deleted,
        oa.cdc_last_update_date,
        oa.logical_is_deleted_del,
        oa.tax_invoice_date,
        oa.payment_unit_number
    FROM tmp_cfs_opt_application_inst_t oa
    JOIN (
        SELECT DISTINCT ccci.invoice_no, ccci.application_code, ccci.send_date
        FROM tmp_zx_send_countersign_t ccci
        WHERE ccci.status >= 40
          AND (ccci.office_receive_date IS NULL OR ccci.customer_receive_date IS NULL)
    ) tic ON tic.application_code = oa.application_code
    WHERE oa.status = 50
),
fact_t AS (
    SELECT * FROM approval_temp
    UNION ALL
    SELECT * FROM send_temp
    UNION ALL
    SELECT * FROM countersign_temp
)

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
    CAST(epoch_ms(CURRENT_TIMESTAMP) AS VARCHAR) AS _hoodie_event_time,
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
FROM fact_t
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
    AND fact_t.cdc_last_update_date >= f.job_last_start_date - INTERVAL 30 MINUTE
) TO '__WORK_DIR__/current/output/q1_detail_live.csv' (HEADER, DELIMITER ',');
