-- SOURCE_FILE: (generated)
-- TRANSFORMATIONS: DELETE using temp key tables

DELETE FROM s000_cqrs_cfs.cfs_cfg_company_t AS t USING _dk_cfs_cfg_company_t AS dk WHERE t.company_id = dk.company_id;
DELETE FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t AS t USING _dk_cfs_cinv_customer_invoice_t AS dk WHERE t.customer_invoice_id = dk.customer_invoice_id;
DELETE FROM s000_cqrs_cfs.cfs_con_payment_unit_t AS t USING _dk_cfs_con_payment_unit_t AS dk WHERE t.payment_unit_id = dk.payment_unit_id;
DELETE FROM s000_cqrs_cfs.cfs_inv_invoice_info_t AS t USING _dk_cfs_inv_invoice_info_t AS dk WHERE t.invoice_id = dk.invoice_id;
DELETE FROM s000_cqrs_cfs.cfs_opt_application_inst_t AS t USING _dk_cfs_opt_application_inst_t AS dk WHERE t.application_inst_id = dk.application_inst_id;
DELETE FROM s000_cqrs_cfs.cfs_opt_application_t AS t USING _dk_cfs_opt_application_t AS dk WHERE t.operator_application_id = dk.operator_application_id;
DELETE FROM s000_cqrs_cfs.cfs_proc_route_t AS t USING _dk_cfs_proc_route_t AS dk WHERE t.route_id = dk.route_id;
DELETE FROM s000_cqrs_cfs.cfs_proc_task_t AS t USING _dk_cfs_proc_task_t AS dk WHERE t.task_id = dk.task_id;
DELETE FROM s000_cqrs_cfs.tpl_fd_message_t AS t USING _dk_tpl_fd_message_t AS dk WHERE t.message_id = dk.message_id;
DELETE FROM s000_cqrs_cfs.tpl_user_t AS t USING _dk_tpl_user_t AS dk WHERE t.user_id = dk.user_id;
DELETE FROM s000_dwt_hws_iao.cfs_comm_contract_t AS t USING _dk_cfs_comm_contract_t AS dk WHERE t.contract_id = dk.contract_id;

-- Drop temp key tables
DROP TABLE IF EXISTS _dk_cfs_cfg_company_t;
DROP TABLE IF EXISTS _dk_cfs_cinv_customer_invoice_t;
DROP TABLE IF EXISTS _dk_cfs_con_payment_unit_t;
DROP TABLE IF EXISTS _dk_cfs_inv_invoice_info_t;
DROP TABLE IF EXISTS _dk_cfs_opt_application_inst_t;
DROP TABLE IF EXISTS _dk_cfs_opt_application_t;
DROP TABLE IF EXISTS _dk_cfs_proc_route_t;
DROP TABLE IF EXISTS _dk_cfs_proc_task_t;
DROP TABLE IF EXISTS _dk_tpl_fd_message_t;
DROP TABLE IF EXISTS _dk_tpl_user_t;
DROP TABLE IF EXISTS _dk_cfs_comm_contract_t;
