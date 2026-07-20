-- SOURCE_FILE: create_matview.sql
-- SOURCE_OBJECT: all 9 materialized view definitions
-- METHOD: ivm
-- QUERY_FORM: init
-- TRANSFORMATIONS: physical materialized tables maintained by translated Job 5 IVM SQL; DuckDB CTAS

-- Create physical materialized tables via CTAS from the view definitions
-- These are physical tables, NOT native materialized views

CREATE TABLE tmp_zx_send_countersign_t_mv AS
SELECT ccci.application_code, ccci.approve_date, ccci.status, ccci.invoice_no,
    ccci.send_date, ccci.office_receive_date, ccci.customer_receive_date,
    ccci.tax_invoice_date, '1' AS type, ccci.customer_invoice_id AS src_pk
FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t ccci WHERE ccci.status >= 3
UNION ALL
SELECT cici.application_code, cici.approve_date, cici.status,
    cici.tax_invoice_no AS invoice_no, cici.send_date,
    NULL AS office_receive_date, NULL AS customer_receive_date,
    NULL AS tax_invoice_date, '2' AS type, cici.invoice_id AS src_pk
FROM s000_cqrs_cfs.cfs_inv_invoice_info_t cici WHERE cici.status IN (30, 40);

CREATE TABLE apt_mv AS
SELECT application_code, MAX(tax_invoice_date) AS tax_invoice_date,
    COUNT(*) AS _ivm_count
FROM tmp_zx_send_countersign_t_mv WHERE type = '1'
GROUP BY application_code;

CREATE TABLE tmp_cfs_opt_application_inst_t_mv AS
SELECT opii.application_inst_id, oa.operator_application_id, oa.application_code,
    oa.salesperson_id, oa.company_id, oa.customer_id, opii.contract_id,
    oa.currency_id, oa.total_amount, oa.creation_date, oa.applicant_time,
    oa.logical_is_deleted,
    GREATEST(oa.cdc_last_update_date, opii.cdc_last_update_date) AS cdc_last_update_date,
    oa.work_flow_id, oa.application_type, oa.status,
    GREATEST(CAST(oa.logical_is_deleted AS INTEGER), CAST(opii.logical_is_deleted AS INTEGER))::BOOLEAN AS logical_is_deleted_del,
    opii.payment_unit_id, pu.payment_unit_number, apt.tax_invoice_date
FROM s000_cqrs_cfs.cfs_opt_application_t oa
JOIN s000_cqrs_cfs.cfs_opt_application_inst_t opii ON oa.operator_application_id = opii.operator_application_id
LEFT JOIN s000_cqrs_cfs.cfs_con_payment_unit_t pu ON opii.payment_unit_id = pu.payment_unit_id
LEFT JOIN apt_mv apt ON oa.application_code = apt.application_code
WHERE oa.application_type = 1 AND oa.status IN (30, 40, 50)
  AND oa.creation_date > TIMESTAMP '2022-01-01 00:00:00';

CREATE TABLE approval_temp_mv AS
SELECT oa.application_inst_id AS id, CAST(oa.operator_application_id AS VARCHAR) AS head_id,
    oa.application_code,
    CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
    oa.operator_application_id AS business_id,
    '税票' AS bill_type, '正项' AS business_type, '待审批' AS node_type,
    -999 AS invoice_type_id, oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
    CAST(NULL AS BIGINT) AS invoice_id, CAST(NULL AS VARCHAR) AS invoice_no,
    oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
    oa.currency_id, oa.total_amount, oa.creation_date,
    oa.applicant_time AS submit_date, oa.applicant_time,
    CAST(NULL AS BIGINT) AS current_handler_id, node.node_define_name_cn AS currentrole,
    CAST(NULL AS BIGINT) AS todo_billing_id, CAST(NULL AS BIGINT) AS payment_unit_id,
    CAST(NULL AS VARCHAR) AS source_code, CAST(NULL AS VARCHAR) AS details_flag,
    CAST(NULL AS VARCHAR) AS billing_status,
    oa.logical_is_deleted, oa.cdc_last_update_date, oa.logical_is_deleted_del,
    oa.tax_invoice_date, oa.payment_unit_number
FROM tmp_cfs_opt_application_inst_t_mv oa
LEFT JOIN s000_cqrs_cfs.cfs_proc_task_t task ON oa.work_flow_id = task.proc_inst_id
LEFT JOIN s000_cqrs_cfs.cfs_proc_route_t route ON task.route_id = route.route_id
LEFT JOIN s000_cqrs_cfs.cfs_proc_node_define_t node ON route.node_define_id = node.node_define_id
WHERE oa.status = 30;

CREATE TABLE temp_mv AS
SELECT t.application_code, MAX(t.approve_date) AS approve_date,
    COUNT(*) AS _ivm_count
FROM tmp_zx_send_countersign_t_mv t WHERE t.status = 30
GROUP BY t.application_code;

CREATE TABLE send_temp_mv AS
SELECT oa.application_inst_id AS id, CAST(oa.operator_application_id AS VARCHAR) AS head_id,
    oa.application_code,
    CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
    oa.operator_application_id AS business_id,
    '税票' AS bill_type, '正项' AS business_type, '待寄送' AS node_type,
    -999 AS invoice_type_id, oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
    CAST(NULL AS BIGINT) AS invoice_id, CAST(NULL AS VARCHAR) AS invoice_no,
    oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
    oa.currency_id, oa.total_amount, oa.creation_date,
    temp.approve_date AS submit_date, oa.applicant_time,
    CAST(NULL AS BIGINT) AS current_handler_id, mes.message AS currentrole,
    CAST(NULL AS BIGINT) AS todo_billing_id, CAST(NULL AS BIGINT) AS payment_unit_id,
    CAST(NULL AS VARCHAR) AS source_code, CAST(NULL AS VARCHAR) AS details_flag,
    CAST(NULL AS VARCHAR) AS billing_status,
    oa.logical_is_deleted, oa.cdc_last_update_date, oa.logical_is_deleted_del,
    oa.tax_invoice_date, oa.payment_unit_number
FROM tmp_cfs_opt_application_inst_t_mv oa
JOIN temp_mv temp ON temp.application_code = oa.application_code
LEFT JOIN s000_cqrs_cfs.tpl_fd_message_t mes
    ON mes.app_name = 'cfs' AND mes.language = 'zh_CN'
    AND mes.message_key = 'cfs.html.label.role.operatorInvoiceSender'
WHERE oa.status = 40;

CREATE TABLE tic_mv AS
SELECT ccci.invoice_no, ccci.application_code, ccci.send_date,
    COUNT(*) AS _ivm_count
FROM tmp_zx_send_countersign_t_mv ccci
WHERE ccci.status >= 40
  AND (ccci.office_receive_date IS NULL OR ccci.customer_receive_date IS NULL)
GROUP BY ccci.invoice_no, ccci.application_code, ccci.send_date;

CREATE TABLE countersign_temp_mv AS
SELECT oa.application_inst_id AS id, CAST(oa.operator_application_id AS VARCHAR) AS head_id,
    oa.application_code,
    CAST(strftime(oa.applicant_time, '%Y%m') AS INTEGER) AS period_id,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_dd,
    CAST(strftime(oa.applicant_time, '%Y%m%d') AS INTEGER) AS period_id_qty,
    oa.operator_application_id AS business_id,
    '税票' AS bill_type, '正项' AS business_type, '待签返' AS node_type,
    -999 AS invoice_type_id, oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
    CAST(NULL AS BIGINT) AS invoice_id, tic.invoice_no,
    oa.operator_application_id, CAST(NULL AS VARCHAR) AS milestone_name,
    oa.currency_id, oa.total_amount, oa.creation_date,
    tic.send_date AS submit_date, oa.applicant_time,
    CAST(NULL AS BIGINT) AS current_handler_id, '结束' AS currentrole,
    CAST(NULL AS BIGINT) AS todo_billing_id, CAST(NULL AS BIGINT) AS payment_unit_id,
    CAST(NULL AS VARCHAR) AS source_code, CAST(NULL AS VARCHAR) AS details_flag,
    CAST(NULL AS VARCHAR) AS billing_status,
    oa.logical_is_deleted, oa.cdc_last_update_date, oa.logical_is_deleted_del,
    oa.tax_invoice_date, oa.payment_unit_number
FROM tmp_cfs_opt_application_inst_t_mv oa
JOIN tic_mv tic ON tic.application_code = oa.application_code
WHERE oa.status = 50;

CREATE TABLE fact_t_mv AS
SELECT id, head_id, application_code, period_id, period_id_dd, period_id_qty,
    business_id, bill_type, business_type, node_type, invoice_type_id,
    salesperson_id, company_id, customer_id, contract_id,
    invoice_id, invoice_no, operator_application_id, milestone_name,
    currency_id, total_amount, creation_date, submit_date, applicant_time,
    current_handler_id, currentrole, todo_billing_id, payment_unit_id,
    source_code, details_flag, billing_status, logical_is_deleted,
    cdc_last_update_date, tax_invoice_date, payment_unit_number
FROM approval_temp_mv
UNION ALL
SELECT id, head_id, application_code, period_id, period_id_dd, period_id_qty,
    business_id, bill_type, business_type, node_type, invoice_type_id,
    salesperson_id, company_id, customer_id, contract_id,
    invoice_id, invoice_no, operator_application_id, milestone_name,
    currency_id, total_amount, creation_date, submit_date, applicant_time,
    current_handler_id, currentrole, todo_billing_id, payment_unit_id,
    source_code, details_flag, billing_status, logical_is_deleted,
    cdc_last_update_date, tax_invoice_date, payment_unit_number
FROM send_temp_mv
UNION ALL
SELECT id, head_id, application_code, period_id, period_id_dd, period_id_qty,
    business_id, bill_type, business_type, node_type, invoice_type_id,
    salesperson_id, company_id, customer_id, contract_id,
    invoice_id, invoice_no, operator_application_id, milestone_name,
    currency_id, total_amount, creation_date, submit_date, applicant_time,
    current_handler_id, currentrole, todo_billing_id, payment_unit_id,
    source_code, details_flag, billing_status, logical_is_deleted,
    cdc_last_update_date, tax_invoice_date, payment_unit_number
FROM countersign_temp_mv;
