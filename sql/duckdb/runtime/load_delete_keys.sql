-- SOURCE_FILE: (generated)
-- TRANSFORMATIONS: Load delete keys into temp tables from fixed slots

CREATE OR REPLACE TEMP TABLE _dk_cfs_cfg_company_t (company_id BIGINT);
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_cfg_company_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_cfg_company_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_cfg_company_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_cfg_company_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cfg_company_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_cfg_company_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_cinv_customer_invoice_t (customer_invoice_id BIGINT);
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_con_payment_unit_t (payment_unit_id BIGINT);
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_con_payment_unit_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_inv_invoice_info_t (invoice_id BIGINT);
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_opt_application_inst_t (application_inst_id BIGINT);
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_inst_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_opt_application_t (operator_application_id BIGINT);
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_opt_application_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_opt_application_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_opt_application_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_opt_application_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_opt_application_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_opt_application_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_proc_route_t (route_id BIGINT);
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_proc_route_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_proc_route_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_proc_route_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_proc_route_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_route_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_proc_route_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_proc_task_t (task_id BIGINT);
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.cfs_proc_task_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.cfs_proc_task_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.cfs_proc_task_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.cfs_proc_task_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_proc_task_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.cfs_proc_task_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_tpl_fd_message_t (message_id BIGINT);
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.tpl_fd_message_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.tpl_fd_message_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.tpl_fd_message_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.tpl_fd_message_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_fd_message_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.tpl_fd_message_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_tpl_user_t (user_id BIGINT);
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_01/s000_cqrs_cfs.tpl_user_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_02/s000_cqrs_cfs.tpl_user_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_03/s000_cqrs_cfs.tpl_user_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_04/s000_cqrs_cfs.tpl_user_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_tpl_user_t FROM '__WORK_DIR__/current/delete/slot_05/s000_cqrs_cfs.tpl_user_t.csv' (HEADER true, DELIMITER ',');

CREATE OR REPLACE TEMP TABLE _dk_cfs_comm_contract_t (contract_id BIGINT);
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_01/s000_dwt_hws_iao.cfs_comm_contract_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_02/s000_dwt_hws_iao.cfs_comm_contract_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_03/s000_dwt_hws_iao.cfs_comm_contract_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_04/s000_dwt_hws_iao.cfs_comm_contract_t.csv' (HEADER true, DELIMITER ',');
COPY _dk_cfs_comm_contract_t FROM '__WORK_DIR__/current/delete/slot_05/s000_dwt_hws_iao.cfs_comm_contract_t.csv' (HEADER true, DELIMITER ',');

