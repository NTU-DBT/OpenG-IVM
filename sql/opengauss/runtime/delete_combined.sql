-- SOURCE_FILE: (generated)
-- TRANSFORMATIONS: Load delete keys into temp tables from fixed slots

DROP TABLE IF EXISTS _dk_cfs_cfg_company_t;
CREATE TEMP TABLE _dk_cfs_cfg_company_t (company_id BIGINT);
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_cinv_customer_invoice_t;
CREATE TEMP TABLE _dk_cfs_cinv_customer_invoice_t (customer_invoice_id BIGINT);
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_con_payment_unit_t;
CREATE TEMP TABLE _dk_cfs_con_payment_unit_t (payment_unit_id BIGINT);
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_inv_invoice_info_t;
CREATE TEMP TABLE _dk_cfs_inv_invoice_info_t (invoice_id BIGINT);
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_opt_application_inst_t;
CREATE TEMP TABLE _dk_cfs_opt_application_inst_t (application_inst_id BIGINT);
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_opt_application_t;
CREATE TEMP TABLE _dk_cfs_opt_application_t (operator_application_id BIGINT);
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_proc_route_t;
CREATE TEMP TABLE _dk_cfs_proc_route_t (route_id BIGINT);
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_proc_task_t;
CREATE TEMP TABLE _dk_cfs_proc_task_t (task_id BIGINT);
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_tpl_fd_message_t;
CREATE TEMP TABLE _dk_tpl_fd_message_t (message_id BIGINT);
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_tpl_user_t;
CREATE TEMP TABLE _dk_tpl_user_t (user_id BIGINT);
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

DROP TABLE IF EXISTS _dk_cfs_comm_contract_t;
CREATE TEMP TABLE _dk_cfs_comm_contract_t (contract_id BIGINT);
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_01/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_02/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_03/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_04/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_05/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- SOURCE_FILE: (generated)
-- TRANSFORMATIONS: DELETE using temp key tables

DELETE FROM s000_cqrs_cfs.cfs_cfg_company_t t USING _dk_cfs_cfg_company_t AS dk WHERE t.company_id = dk.company_id;
DELETE FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t t USING _dk_cfs_cinv_customer_invoice_t AS dk WHERE t.customer_invoice_id = dk.customer_invoice_id;
DELETE FROM s000_cqrs_cfs.cfs_con_payment_unit_t t USING _dk_cfs_con_payment_unit_t AS dk WHERE t.payment_unit_id = dk.payment_unit_id;
DELETE FROM s000_cqrs_cfs.cfs_inv_invoice_info_t t USING _dk_cfs_inv_invoice_info_t AS dk WHERE t.invoice_id = dk.invoice_id;
DELETE FROM s000_cqrs_cfs.cfs_opt_application_inst_t t USING _dk_cfs_opt_application_inst_t AS dk WHERE t.application_inst_id = dk.application_inst_id;
DELETE FROM s000_cqrs_cfs.cfs_opt_application_t t USING _dk_cfs_opt_application_t AS dk WHERE t.operator_application_id = dk.operator_application_id;
DELETE FROM s000_cqrs_cfs.cfs_proc_route_t t USING _dk_cfs_proc_route_t AS dk WHERE t.route_id = dk.route_id;
DELETE FROM s000_cqrs_cfs.cfs_proc_task_t t USING _dk_cfs_proc_task_t AS dk WHERE t.task_id = dk.task_id;
DELETE FROM s000_cqrs_cfs.tpl_fd_message_t t USING _dk_tpl_fd_message_t AS dk WHERE t.message_id = dk.message_id;
DELETE FROM s000_cqrs_cfs.tpl_user_t t USING _dk_tpl_user_t AS dk WHERE t.user_id = dk.user_id;
DELETE FROM s000_dwt_hws_iao.cfs_comm_contract_t t USING _dk_cfs_comm_contract_t AS dk WHERE t.contract_id = dk.contract_id;

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
