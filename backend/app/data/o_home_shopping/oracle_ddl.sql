-- O-Home-Shopping v2.0 Oracle SQL staging DDL.
-- Load vertex tables first, then edge tables. All dates/times are KST and all money columns are KRW.

CREATE TABLE ohv2_customer (
  customer_id VARCHAR2(48),
  segment_id VARCHAR2(48),
  region_id VARCHAR2(48),
  age_band VARCHAR2(240),
  gender_code VARCHAR2(240),
  loyalty_tier VARCHAR2(240),
  signup_month VARCHAR2(240),
  privacy_level VARCHAR2(240),
  synthetic_flag CHAR(1),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_customer PRIMARY KEY (customer_id)
);

CREATE TABLE ohv2_customer_segment (
  segment_id VARCHAR2(48),
  segment_name_ko VARCHAR2(500),
  description_ko VARCHAR2(500),
  spending_power_factor NUMBER(14,6),
  mobile_affinity_factor NUMBER(14,6),
  return_propensity NUMBER(14,6),
  CONSTRAINT pk_ohv2_customer_segment PRIMARY KEY (segment_id)
);

CREATE TABLE ohv2_region (
  region_id VARCHAR2(48),
  sido VARCHAR2(240),
  sigungu VARCHAR2(240),
  region_type VARCHAR2(240),
  island_mountain_flag CHAR(1),
  population_weight NUMBER(14,6),
  logistics_risk_factor NUMBER(14,6),
  privacy_level VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_region PRIMARY KEY (region_id)
);

CREATE TABLE ohv2_host (
  host_id VARCHAR2(48),
  host_alias VARCHAR2(240),
  host_gender_code VARCHAR2(240),
  host_gender_ko VARCHAR2(500),
  host_age_years NUMBER(14),
  host_type VARCHAR2(240),
  host_star_tier VARCHAR2(240),
  is_star_host CHAR(1),
  star_category_rank NUMBER(14),
  primary_category_id VARCHAR2(48),
  secondary_category_ids VARCHAR2(240),
  preferred_time_slots VARCHAR2(240),
  sales_lift_factor NUMBER(14,6),
  sold_out_lift_factor NUMBER(14,6),
  return_risk_factor NUMBER(14,6),
  appearance_capacity_monthly NUMBER(14),
  max_daily_broadcasts NUMBER(14),
  sales_share_power NUMBER(14,6),
  host_photo_object_name VARCHAR2(500),
  host_photo_url VARCHAR2(1000),
  synthetic_flag CHAR(1),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_host PRIMARY KEY (host_id)
);

CREATE TABLE ohv2_product (
  product_id VARCHAR2(48),
  product_name_ko VARCHAR2(500),
  brand_id VARCHAR2(48),
  category_id VARCHAR2(48),
  category_large_ko VARCHAR2(500),
  category_middle_ko VARCHAR2(500),
  list_price_krw NUMBER(18,2),
  sale_price_krw NUMBER(18,2),
  discount_rate NUMBER(14,6),
  margin_rate NUMBER(14,6),
  is_premium CHAR(1),
  is_exclusive CHAR(1),
  is_bundle CHAR(1),
  seasonality_tags VARCHAR2(240),
  import_cost_sensitivity NUMBER(14,6),
  synthetic_flag CHAR(1),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_product PRIMARY KEY (product_id)
);

CREATE TABLE ohv2_sku (
  sku_id VARCHAR2(48),
  product_id VARCHAR2(48),
  sku_name_ko VARCHAR2(500),
  option_name_ko VARCHAR2(500),
  list_price_krw NUMBER(18,2),
  sale_price_krw NUMBER(18,2),
  base_inventory_level NUMBER(14),
  active_flag CHAR(1),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_sku PRIMARY KEY (sku_id)
);

CREATE TABLE ohv2_brand (
  brand_id VARCHAR2(48),
  brand_name_ko VARCHAR2(500),
  primary_category_id VARCHAR2(48),
  brand_tier VARCHAR2(240),
  domestic_or_import VARCHAR2(240),
  synthetic_flag CHAR(1),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_brand PRIMARY KEY (brand_id)
);

CREATE TABLE ohv2_category (
  category_id VARCHAR2(48),
  category_large_ko VARCHAR2(500),
  category_middle_values_ko VARCHAR2(500),
  min_price_krw NUMBER(18,2),
  max_price_krw NUMBER(18,2),
  cancel_rate_min NUMBER(14,6),
  cancel_rate_max NUMBER(14,6),
  return_rate_min NUMBER(14,6),
  return_rate_max NUMBER(14,6),
  sales_factor NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_category PRIMARY KEY (category_id)
);

CREATE TABLE ohv2_broadcast (
  broadcast_id VARCHAR2(48),
  broadcast_date DATE,
  start_datetime_kst TIMESTAMP,
  end_datetime_kst TIMESTAMP,
  duration_min NUMBER(14),
  channel_id VARCHAR2(48),
  program_id VARCHAR2(48),
  broadcast_slot_id VARCHAR2(48),
  time_bucket_id VARCHAR2(48),
  primary_category_id VARCHAR2(48),
  title_ko VARCHAR2(500),
  planning_theme_ko VARCHAR2(500),
  planning_reason_ko VARCHAR2(500),
  schedule_priority VARCHAR2(240),
  emergency_replacement_flag CHAR(1),
  source_sold_out_broadcast_id VARCHAR2(48),
  is_live CHAR(1),
  is_prime_time CHAR(1),
  slot_commission_rate NUMBER(14,6),
  airtime_cost_krw NUMBER(18,2),
  product_cost_krw NUMBER(18,2),
  broadcast_margin_krw NUMBER(18,2),
  planned_product_count NUMBER(14),
  active_event_count NUMBER(14),
  active_season_count NUMBER(14),
  viewer_uv NUMBER(14),
  app_inflow_count NUMBER(14),
  gross_sales_krw NUMBER(18,2),
  net_sales_krw NUMBER(18,2),
  order_count_weighted VARCHAR2(240),
  sample_order_count NUMBER(14),
  conversion_rate NUMBER(14,6),
  timezone VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast PRIMARY KEY (broadcast_id)
);

CREATE TABLE ohv2_broadcast_slot (
  broadcast_slot_id VARCHAR2(48),
  time_slot VARCHAR2(240),
  slot_start_hour NUMBER(14),
  slot_end_hour NUMBER(14),
  is_prime_time CHAR(1),
  slot_label_ko VARCHAR2(500),
  timezone VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_slot PRIMARY KEY (broadcast_slot_id)
);

CREATE TABLE ohv2_program (
  program_id VARCHAR2(48),
  program_name_ko VARCHAR2(500),
  channel_id VARCHAR2(48),
  primary_category_id VARCHAR2(48),
  program_type VARCHAR2(240),
  target_segment VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_program PRIMARY KEY (program_id)
);

CREATE TABLE ohv2_channel (
  channel_id VARCHAR2(48),
  channel_type VARCHAR2(240),
  channel_name_ko VARCHAR2(500),
  description_ko VARCHAR2(500),
  is_live_channel CHAR(1),
  annual_broadcast_target NUMBER(14),
  timezone VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_channel PRIMARY KEY (channel_id)
);

CREATE TABLE ohv2_order_txn (
  order_id VARCHAR2(48),
  customer_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  order_datetime_kst TIMESTAMP,
  order_channel VARCHAR2(240),
  payment_method VARCHAR2(240),
  order_status VARCHAR2(240),
  gross_amount_krw NUMBER(18,2),
  discount_amount_krw NUMBER(18,2),
  net_amount_krw NUMBER(18,2),
  representative_gross_amount_krw NUMBER(18,2),
  representative_net_amount_krw NUMBER(18,2),
  sample_weight NUMBER(14,6),
  revenue_weight NUMBER(14,6),
  timezone VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_txn PRIMARY KEY (order_id)
);

CREATE TABLE ohv2_order_line (
  order_line_id VARCHAR2(48),
  order_id VARCHAR2(48),
  product_id VARCHAR2(48),
  sku_id VARCHAR2(48),
  performance_id VARCHAR2(48),
  quantity VARCHAR2(240),
  representative_quantity NUMBER(14),
  unit_sale_price_krw NUMBER(18,2),
  line_gross_amount_krw NUMBER(18,2),
  line_discount_amount_krw NUMBER(18,2),
  line_net_amount_krw NUMBER(18,2),
  representative_gross_amount_krw NUMBER(18,2),
  representative_net_amount_krw NUMBER(18,2),
  line_status VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_line PRIMARY KEY (order_line_id)
);

CREATE TABLE ohv2_broadcast_product_performance (
  performance_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  product_id VARCHAR2(48),
  sku_id VARCHAR2(48),
  initial_inventory NUMBER(14),
  target_quantity NUMBER(14),
  sold_quantity NUMBER(14),
  gross_sales_krw NUMBER(18,2),
  net_sales_krw NUMBER(18,2),
  discount_amount_krw NUMBER(18,2),
  sell_through_rate NUMBER(14,6),
  sold_out_flag CHAR(1),
  sold_out_datetime_kst TIMESTAMP,
  minutes_to_sold_out VARCHAR2(240),
  missed_demand_quantity NUMBER(14),
  replacement_order_quantity NUMBER(14),
  host_lift_factor NUMBER(14,6),
  event_lift_factor NUMBER(14,6),
  season_lift_factor NUMBER(14,6),
  sample_line_count NUMBER(14),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_product_performance PRIMARY KEY (performance_id)
);

CREATE TABLE ohv2_inventory_snapshot (
  snapshot_id VARCHAR2(48),
  performance_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  sku_id VARCHAR2(48),
  snapshot_datetime_kst TIMESTAMP,
  inventory_stage VARCHAR2(240),
  remaining_inventory NUMBER(14),
  sold_quantity_cumulative VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_inventory_snapshot PRIMARY KEY (snapshot_id)
);

CREATE TABLE ohv2_shipment (
  shipment_id VARCHAR2(48),
  order_id VARCHAR2(48),
  region_id VARCHAR2(48),
  carrier_name VARCHAR2(500),
  delivery_type VARCHAR2(240),
  dispatch_datetime_kst TIMESTAMP,
  delivered_datetime_kst TIMESTAMP,
  delivery_status VARCHAR2(240),
  delay_flag CHAR(1),
  delay_reason VARCHAR2(240),
  shipping_fee_krw NUMBER(18,2),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_shipment PRIMARY KEY (shipment_id)
);

CREATE TABLE ohv2_return_exchange (
  return_id VARCHAR2(48),
  order_id VARCHAR2(48),
  return_type VARCHAR2(240),
  return_reason VARCHAR2(240),
  requested_datetime_kst TIMESTAMP,
  completed_datetime_kst TIMESTAMP,
  refund_amount_krw NUMBER(18,2),
  representative_refund_amount_krw NUMBER(18,2),
  return_status VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_return_exchange PRIMARY KEY (return_id)
);

CREATE TABLE ohv2_promotion (
  promotion_id VARCHAR2(48),
  promotion_name_ko VARCHAR2(500),
  promotion_type VARCHAR2(240),
  start_datetime_kst TIMESTAMP,
  end_datetime_kst TIMESTAMP,
  channel_scope VARCHAR2(240),
  category_scope VARCHAR2(240),
  discount_rate NUMBER(14,6),
  uplift_factor NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_promotion PRIMARY KEY (promotion_id)
);

CREATE TABLE ohv2_event_calendar (
  event_id VARCHAR2(48),
  event_name VARCHAR2(500),
  event_type VARCHAR2(240),
  start_date DATE,
  end_date DATE,
  peak_date DATE,
  impact_start_date DATE,
  impact_end_date DATE,
  impact_window_days NUMBER(14),
  impact_direction VARCHAR2(240),
  impact_strength NUMBER(14,6),
  affected_regions VARCHAR2(240),
  affected_channels VARCHAR2(240),
  affected_categories VARCHAR2(240),
  affected_metrics VARCHAR2(240),
  consumer_sentiment_factor NUMBER(14,6),
  traffic_shift_factor NUMBER(14,6),
  logistics_delay_factor NUMBER(14,6),
  import_cost_factor NUMBER(14,6),
  discretionary_spend_factor NUMBER(14,6),
  korea_relevance VARCHAR2(240),
  explanation VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  source_note VARCHAR2(500),
  CONSTRAINT pk_ohv2_event_calendar PRIMARY KEY (event_id)
);

CREATE TABLE ohv2_season_calendar (
  season_id VARCHAR2(48),
  season_name VARCHAR2(500),
  start_date DATE,
  end_date DATE,
  affected_categories VARCHAR2(240),
  season_lift_factor NUMBER(14,6),
  description VARCHAR2(240),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_season_calendar PRIMARY KEY (season_id)
);

CREATE TABLE ohv2_time_bucket (
  time_bucket_id VARCHAR2(48),
  calendar_date DATE,
  year_no NUMBER(14),
  month_no NUMBER(14),
  day_no NUMBER(14),
  day_of_week_ko VARCHAR2(500),
  time_slot VARCHAR2(240),
  slot_label_ko VARCHAR2(500),
  is_weekend CHAR(1),
  is_prime_time CHAR(1),
  timezone VARCHAR2(240),
  CONSTRAINT pk_ohv2_time_bucket PRIMARY KEY (time_bucket_id)
);

CREATE TABLE ohv2_customer_placed_order (
  edge_id VARCHAR2(48),
  customer_id VARCHAR2(48),
  order_id VARCHAR2(48),
  order_datetime_kst TIMESTAMP,
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_customer_placed_order PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_customer_placed_order_src FOREIGN KEY (customer_id) REFERENCES ohv2_customer (customer_id),
  CONSTRAINT fk_ohv2_customer_placed_order_dst FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id)
);

CREATE TABLE ohv2_order_from_broadcast (
  edge_id VARCHAR2(48),
  order_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_from_broadcast PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_order_from_broadcast_src FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id),
  CONSTRAINT fk_ohv2_order_from_broadcast_dst FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id)
);

CREATE TABLE ohv2_order_has_line (
  edge_id VARCHAR2(48),
  order_id VARCHAR2(48),
  order_line_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_has_line PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_order_has_line_src FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id),
  CONSTRAINT fk_ohv2_order_has_line_dst FOREIGN KEY (order_line_id) REFERENCES ohv2_order_line (order_line_id)
);

CREATE TABLE ohv2_line_for_product (
  edge_id VARCHAR2(48),
  order_line_id VARCHAR2(48),
  product_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_line_for_product PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_line_for_product_src FOREIGN KEY (order_line_id) REFERENCES ohv2_order_line (order_line_id),
  CONSTRAINT fk_ohv2_line_for_product_dst FOREIGN KEY (product_id) REFERENCES ohv2_product (product_id)
);

CREATE TABLE ohv2_line_for_sku (
  edge_id VARCHAR2(48),
  order_line_id VARCHAR2(48),
  sku_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_line_for_sku PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_line_for_sku_src FOREIGN KEY (order_line_id) REFERENCES ohv2_order_line (order_line_id),
  CONSTRAINT fk_ohv2_line_for_sku_dst FOREIGN KEY (sku_id) REFERENCES ohv2_sku (sku_id)
);

CREATE TABLE ohv2_order_has_shipment (
  edge_id VARCHAR2(48),
  order_id VARCHAR2(48),
  shipment_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_has_shipment PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_order_has_shipment_src FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id),
  CONSTRAINT fk_ohv2_order_has_shipment_dst FOREIGN KEY (shipment_id) REFERENCES ohv2_shipment (shipment_id)
);

CREATE TABLE ohv2_order_has_return (
  edge_id VARCHAR2(48),
  order_id VARCHAR2(48),
  return_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_order_has_return PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_order_has_return_src FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id),
  CONSTRAINT fk_ohv2_order_has_return_dst FOREIGN KEY (return_id) REFERENCES ohv2_return_exchange (return_id)
);

CREATE TABLE ohv2_promotion_applied_to_order (
  edge_id VARCHAR2(48),
  promotion_id VARCHAR2(48),
  order_id VARCHAR2(48),
  discount_rate NUMBER(14,6),
  discount_amount_krw NUMBER(18,2),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_promotion_applied_to_order PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_promotion_applied_to_order_src FOREIGN KEY (promotion_id) REFERENCES ohv2_promotion (promotion_id),
  CONSTRAINT fk_ohv2_promotion_applied_to_order_dst FOREIGN KEY (order_id) REFERENCES ohv2_order_txn (order_id)
);

CREATE TABLE ohv2_host_specialized_in_category (
  edge_id VARCHAR2(48),
  host_id VARCHAR2(48),
  category_id VARCHAR2(48),
  specialty_rank NUMBER(14),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_host_specialized_in_category PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_host_specialized_in_category_src FOREIGN KEY (host_id) REFERENCES ohv2_host (host_id),
  CONSTRAINT fk_ohv2_host_specialized_in_category_dst FOREIGN KEY (category_id) REFERENCES ohv2_category (category_id)
);

CREATE TABLE ohv2_product_of_brand (
  edge_id VARCHAR2(48),
  product_id VARCHAR2(48),
  brand_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_product_of_brand PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_product_of_brand_src FOREIGN KEY (product_id) REFERENCES ohv2_product (product_id),
  CONSTRAINT fk_ohv2_product_of_brand_dst FOREIGN KEY (brand_id) REFERENCES ohv2_brand (brand_id)
);

CREATE TABLE ohv2_product_in_category (
  edge_id VARCHAR2(48),
  product_id VARCHAR2(48),
  category_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_product_in_category PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_product_in_category_src FOREIGN KEY (product_id) REFERENCES ohv2_product (product_id),
  CONSTRAINT fk_ohv2_product_in_category_dst FOREIGN KEY (category_id) REFERENCES ohv2_category (category_id)
);

CREATE TABLE ohv2_product_has_sku (
  edge_id VARCHAR2(48),
  product_id VARCHAR2(48),
  sku_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_product_has_sku PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_product_has_sku_src FOREIGN KEY (product_id) REFERENCES ohv2_product (product_id),
  CONSTRAINT fk_ohv2_product_has_sku_dst FOREIGN KEY (sku_id) REFERENCES ohv2_sku (sku_id)
);

CREATE TABLE ohv2_event_impacted_category (
  edge_id VARCHAR2(48),
  event_id VARCHAR2(48),
  category_id VARCHAR2(48),
  impact_strength NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_event_impacted_category PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_event_impacted_category_src FOREIGN KEY (event_id) REFERENCES ohv2_event_calendar (event_id),
  CONSTRAINT fk_ohv2_event_impacted_category_dst FOREIGN KEY (category_id) REFERENCES ohv2_category (category_id)
);

CREATE TABLE ohv2_season_impacted_category (
  edge_id VARCHAR2(48),
  season_id VARCHAR2(48),
  category_id VARCHAR2(48),
  season_lift_factor NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_season_impacted_category PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_season_impacted_category_src FOREIGN KEY (season_id) REFERENCES ohv2_season_calendar (season_id),
  CONSTRAINT fk_ohv2_season_impacted_category_dst FOREIGN KEY (category_id) REFERENCES ohv2_category (category_id)
);

CREATE TABLE ohv2_customer_belongs_to_segment (
  edge_id VARCHAR2(48),
  customer_id VARCHAR2(48),
  segment_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_customer_belongs_to_segment PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_customer_belongs_to_segment_src FOREIGN KEY (customer_id) REFERENCES ohv2_customer (customer_id),
  CONSTRAINT fk_ohv2_customer_belongs_to_segment_dst FOREIGN KEY (segment_id) REFERENCES ohv2_customer_segment (segment_id)
);

CREATE TABLE ohv2_customer_in_region (
  edge_id VARCHAR2(48),
  customer_id VARCHAR2(48),
  region_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_customer_in_region PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_customer_in_region_src FOREIGN KEY (customer_id) REFERENCES ohv2_customer (customer_id),
  CONSTRAINT fk_ohv2_customer_in_region_dst FOREIGN KEY (region_id) REFERENCES ohv2_region (region_id)
);

CREATE TABLE ohv2_broadcast_on_channel (
  edge_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  channel_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_on_channel PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_on_channel_src FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_on_channel_dst FOREIGN KEY (channel_id) REFERENCES ohv2_channel (channel_id)
);

CREATE TABLE ohv2_broadcast_uses_program (
  edge_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  program_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_uses_program PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_uses_program_src FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_uses_program_dst FOREIGN KEY (program_id) REFERENCES ohv2_program (program_id)
);

CREATE TABLE ohv2_broadcast_in_time_bucket (
  edge_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  time_bucket_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_in_time_bucket PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_in_time_bucket_src FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_in_time_bucket_dst FOREIGN KEY (time_bucket_id) REFERENCES ohv2_time_bucket (time_bucket_id)
);

CREATE TABLE ohv2_broadcast_targets_category (
  edge_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  category_id VARCHAR2(48),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_targets_category PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_targets_category_src FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_targets_category_dst FOREIGN KEY (category_id) REFERENCES ohv2_category (category_id)
);

CREATE TABLE ohv2_host_appeared_in_broadcast (
  edge_id VARCHAR2(48),
  host_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  role VARCHAR2(240),
  appearance_order NUMBER(14),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_host_appeared_in_broadcast PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_host_appeared_in_broadcast_src FOREIGN KEY (host_id) REFERENCES ohv2_host (host_id),
  CONSTRAINT fk_ohv2_host_appeared_in_broadcast_dst FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id)
);

CREATE TABLE ohv2_broadcast_features_product (
  edge_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  product_id VARCHAR2(48),
  featured_rank NUMBER(14),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_features_product PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_features_product_src FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_features_product_dst FOREIGN KEY (product_id) REFERENCES ohv2_product (product_id)
);

CREATE TABLE ohv2_broadcast_triggered_emergency_broadcast (
  edge_id VARCHAR2(48),
  source_broadcast_id VARCHAR2(48),
  emergency_broadcast_id VARCHAR2(48),
  trigger_reason_ko VARCHAR2(500),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_broadcast_triggered_emergency_broadcast PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_broadcast_triggered_emergency_broadcast_src FOREIGN KEY (source_broadcast_id) REFERENCES ohv2_broadcast (broadcast_id),
  CONSTRAINT fk_ohv2_broadcast_triggered_emergency_broadcast_dst FOREIGN KEY (emergency_broadcast_id) REFERENCES ohv2_broadcast (broadcast_id)
);

CREATE TABLE ohv2_event_impacted_broadcast (
  edge_id VARCHAR2(48),
  event_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  impact_strength NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_event_impacted_broadcast PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_event_impacted_broadcast_src FOREIGN KEY (event_id) REFERENCES ohv2_event_calendar (event_id),
  CONSTRAINT fk_ohv2_event_impacted_broadcast_dst FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id)
);

CREATE TABLE ohv2_promotion_applied_to_broadcast (
  edge_id VARCHAR2(48),
  promotion_id VARCHAR2(48),
  broadcast_id VARCHAR2(48),
  discount_rate NUMBER(14,6),
  confidence_grade VARCHAR2(240),
  CONSTRAINT pk_ohv2_promotion_applied_to_broadcast PRIMARY KEY (edge_id),
  CONSTRAINT fk_ohv2_promotion_applied_to_broadcast_src FOREIGN KEY (promotion_id) REFERENCES ohv2_promotion (promotion_id),
  CONSTRAINT fk_ohv2_promotion_applied_to_broadcast_dst FOREIGN KEY (broadcast_id) REFERENCES ohv2_broadcast (broadcast_id)
);
