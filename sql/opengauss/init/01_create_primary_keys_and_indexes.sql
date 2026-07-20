-- SOURCE_FILE: create_primary_key_ddl.sql
-- TRANSFORMATIONS: dialect adaptation for openGauss

ALTER TABLE s000_cqrs_cfs.cfs_cfg_company_t ADD PRIMARY KEY (company_id);
ALTER TABLE s000_cqrs_cfs.cfs_cinv_customer_invoice_t ADD PRIMARY KEY (customer_invoice_id);
ALTER TABLE s000_cqrs_cfs.cfs_con_payment_unit_t ADD PRIMARY KEY (payment_unit_id);
ALTER TABLE s000_cqrs_cfs.cfs_inv_invoice_info_t ADD PRIMARY KEY (invoice_id);
ALTER TABLE s000_cqrs_cfs.cfs_opt_application_inst_t ADD PRIMARY KEY (application_inst_id);
ALTER TABLE s000_cqrs_cfs.cfs_opt_application_t ADD PRIMARY KEY (operator_application_id);
ALTER TABLE s000_cqrs_cfs.cfs_proc_node_define_t ADD PRIMARY KEY (node_define_id);
ALTER TABLE s000_cqrs_cfs.cfs_proc_route_t ADD PRIMARY KEY (route_id);
ALTER TABLE s000_cqrs_cfs.cfs_proc_task_t ADD PRIMARY KEY (task_id);
ALTER TABLE s000_cqrs_cfs.tpl_fd_message_t ADD PRIMARY KEY (message_id);
ALTER TABLE s000_cqrs_cfs.tpl_user_t ADD PRIMARY KEY (user_id);
ALTER TABLE s000_dwt_hws_iao.cfs_comm_contract_t ADD PRIMARY KEY (contract_id);
ALTER TABLE s000_dwt_hws_iao.cfs_comm_currencies_t ADD PRIMARY KEY (hw_sf_currencies_id);
ALTER TABLE s000_dwt_hws_iao.cfs_comm_customer_t ADD PRIMARY KEY (customer_id);
ALTER TABLE s000_dwt_hws_iao.cfs_comm_invtype_t ADD PRIMARY KEY (invoice_type_id);
ALTER TABLE s000_dwt_hws_iao.cfs_salesperson_region_t ADD PRIMARY KEY (hw_sf_salesperson_id);
ALTER TABLE s000_dwt_hws_iao.dwd_billing_In_transit_dtl_t_05 ADD PRIMARY KEY (id);
ALTER TABLE s000_dwt_hws_iao.dwd_billing_In_transit_t_05 ADD PRIMARY KEY (head_id);
ALTER TABLE s000_dwt_hws_iao.dwd_job_status_t_05 ADD PRIMARY KEY (id);
