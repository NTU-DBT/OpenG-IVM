-- SOURCE_FILE: normal_test.sql
-- SOURCE_OBJECT: second detail INSERT...SELECT (tombstone)
-- METHOD: recompute
-- QUERY_FORM: minmax
-- TRANSFORMATIONS: removed INSERT target; wrapped in COUNT/MINMAX/export; CTE recompute chain; dialect adaptation
SELECT MIN(q.id) AS min_id, MAX(q.id) AS max_id,
    MIN(q.application_code) AS min_app_code, MAX(q.application_code) AS max_app_code,
    MIN(q.submit_date) AS min_submit_date, MAX(q.submit_date) AS max_submit_date,
    MIN(q.total_amount) AS min_total_amount, MAX(q.total_amount) AS max_total_amount
FROM (
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
        CAST(to_char(oa.applicant_time, 'yyyyMM') AS INTEGER) AS period_id,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_dd,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_qty,
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
        CAST(to_char(oa.applicant_time, 'yyyyMM') AS INTEGER) AS period_id,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_dd,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_qty,
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
        CAST(to_char(oa.applicant_time, 'yyyyMM') AS INTEGER) AS period_id,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_dd,
        CAST(to_char(oa.applicant_time, 'yyyyMMdd') AS INTEGER) AS period_id_qty,
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
        AND NOT EXISTS (SELECT 1 FROM approval_temp oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
    OR (fact_t.node_type IN ('待寄送')
        AND NOT EXISTS (SELECT 1 FROM send_temp oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
    OR (fact_t.node_type IN ('待签返')
        AND NOT EXISTS (SELECT 1 FROM countersign_temp oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id))
) AS q;
