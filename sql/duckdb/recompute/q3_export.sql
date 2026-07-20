-- SOURCE_FILE: normal_test.sql
-- SOURCE_OBJECT: third summary INSERT...SELECT
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
    FROM (SELECT * FROM approval_temp UNION ALL SELECT * FROM send_temp UNION ALL SELECT * FROM countersign_temp) fact_t
    LEFT JOIN s000_dwt_hws_iao.dwd_job_status_t_05 f ON (1 = 1)
    WHERE fact_t.cdc_last_update_date >= f.job_last_start_date - INTERVAL 30 MINUTE
) scp ON t.id = scp.id
GROUP BY t.head_id, t.logical_is_deleted
) TO '__WORK_DIR__/current/output/q3.csv' (HEADER, DELIMITER ',');
