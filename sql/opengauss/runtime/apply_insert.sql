-- SOURCE_FILE: (generated)
-- TRANSFORMATIONS: Fixed-slot COPY for inserting dynamic data
-- Each step inserts SLICES_PER_STEP files per dynamic table

COPY s000_cqrs_cfs.cfs_cfg_company_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cfg_company_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cfg_company_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cfg_company_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cfg_company_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_cfg_company_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_cinv_customer_invoice_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_cinv_customer_invoice_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_con_payment_unit_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_con_payment_unit_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_con_payment_unit_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_con_payment_unit_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_con_payment_unit_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_con_payment_unit_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_inv_invoice_info_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_inv_invoice_info_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_opt_application_inst_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_inst_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_inst_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_inst_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_inst_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_opt_application_inst_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_opt_application_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_opt_application_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_opt_application_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_proc_route_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_route_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_route_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_route_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_route_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_proc_route_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.cfs_proc_task_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_task_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_task_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_task_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.cfs_proc_task_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.cfs_proc_task_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.tpl_fd_message_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_fd_message_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_fd_message_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_fd_message_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_fd_message_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.tpl_fd_message_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_cqrs_cfs.tpl_user_t FROM '__WORK_DIR__/current/insert/slot_01/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_user_t FROM '__WORK_DIR__/current/insert/slot_02/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_user_t FROM '__WORK_DIR__/current/insert/slot_03/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_user_t FROM '__WORK_DIR__/current/insert/slot_04/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_cqrs_cfs.tpl_user_t FROM '__WORK_DIR__/current/insert/slot_05/s000_cqrs_cfs.tpl_user_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY s000_dwt_hws_iao.cfs_comm_contract_t FROM '__WORK_DIR__/current/insert/slot_01/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_dwt_hws_iao.cfs_comm_contract_t FROM '__WORK_DIR__/current/insert/slot_02/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_dwt_hws_iao.cfs_comm_contract_t FROM '__WORK_DIR__/current/insert/slot_03/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_dwt_hws_iao.cfs_comm_contract_t FROM '__WORK_DIR__/current/insert/slot_04/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
COPY s000_dwt_hws_iao.cfs_comm_contract_t FROM '__WORK_DIR__/current/insert/slot_05/s000_dwt_hws_iao.cfs_comm_contract_t.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

