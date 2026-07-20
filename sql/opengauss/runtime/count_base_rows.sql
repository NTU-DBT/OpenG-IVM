-- Count rows in all dynamic base tables
SELECT 's000_cqrs_cfs.cfs_cfg_company_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_cfg_company_t;
SELECT 's000_cqrs_cfs.cfs_cinv_customer_invoice_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t;
SELECT 's000_cqrs_cfs.cfs_con_payment_unit_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_con_payment_unit_t;
SELECT 's000_cqrs_cfs.cfs_inv_invoice_info_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_inv_invoice_info_t;
SELECT 's000_cqrs_cfs.cfs_opt_application_inst_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_opt_application_inst_t;
SELECT 's000_cqrs_cfs.cfs_opt_application_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_opt_application_t;
SELECT 's000_cqrs_cfs.cfs_proc_route_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_proc_route_t;
SELECT 's000_cqrs_cfs.cfs_proc_task_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.cfs_proc_task_t;
SELECT 's000_cqrs_cfs.tpl_fd_message_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.tpl_fd_message_t;
SELECT 's000_cqrs_cfs.tpl_user_t' AS table_name, COUNT(*) AS row_count FROM s000_cqrs_cfs.tpl_user_t;
SELECT 's000_dwt_hws_iao.cfs_comm_contract_t' AS table_name, COUNT(*) AS row_count FROM s000_dwt_hws_iao.cfs_comm_contract_t;
