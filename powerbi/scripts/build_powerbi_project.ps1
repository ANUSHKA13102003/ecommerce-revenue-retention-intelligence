<#
.SYNOPSIS
    Builds and validates the complete Power BI Project (.pbip + TMDL Semantic Model + 5-page Report)
    for E-Commerce Intelligence OS using Power BI Desktop SDK assemblies.
#>
$ErrorActionPreference = 'Stop'

$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$PowerBIDir   = Split-Path -Parent $ScriptDir
$ProjectRoot  = Split-Path -Parent $PowerBIDir
$ProcessedDir = Join-Path $ProjectRoot 'data\processed'
$ExportsDir   = Join-Path $PowerBIDir 'data_exports'
$ThemeSrc     = Join-Path $PowerBIDir 'theme\Enterprise_Light_OS_Theme.json'

# Locate Power BI Desktop installation (Store or MSI)
$PbiBin = $null
$appxPath = $null
try {
    $appx = Get-AppxPackage -Name 'Microsoft.MicrosoftPowerBIDesktop' -ErrorAction Stop | Select-Object -First 1
    if ($appx) { $appxPath = Join-Path $appx.InstallLocation 'bin' }
} catch { }
$candidates = @(
    $appxPath,
    'C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_2.159.1231.0_x64__8wekyb3d8bbwe\bin',
    'C:\Program Files\Microsoft Power BI Desktop\bin',
    'C:\Program Files (x86)\Microsoft Power BI Desktop\bin'
) | Where-Object { $_ }
foreach ($cand in $candidates) {
    if (Test-Path (Join-Path $cand 'Microsoft.PowerBI.Packaging.dll')) {
        $PbiBin = $cand
        break
    }
}
if (-not $PbiBin) {
    throw "Could not locate Power BI Desktop SDK assemblies (Microsoft.PowerBI.Packaging.dll)."
}
Write-Host "Using Power BI Desktop SDK at: $PbiBin"

Add-Type @"
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

public static class PbiSdkResolver {
    private static readonly HashSet<string> Seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    private static string _bin;
    public static void Init(string bin) {
        _bin = bin;
        AppDomain.CurrentDomain.AssemblyResolve += (s, a) => {
            string name = a.Name.Split(',')[0];
            lock (Seen) {
                if (!Seen.Add(name)) return null;
            }
            string p = Path.Combine(_bin, name + ".dll");
            return File.Exists(p) ? Assembly.LoadFrom(p) : null;
        };
    }
}
"@
[PbiSdkResolver]::Init($PbiBin)
Add-Type -Path (Join-Path $PbiBin 'Microsoft.PowerBI.Packaging.dll')
Add-Type -Path (Join-Path $PbiBin 'Microsoft.PowerBI.Tabular.dll')

$PbipPath     = Join-Path $PowerBIDir 'Ecommerce_Intelligence_OS.pbip'
$SmFolder     = Join-Path $PowerBIDir 'Ecommerce_Intelligence_OS.SemanticModel'
$SmDefFolder  = Join-Path $SmFolder 'definition'
$ReportFolder = Join-Path $PowerBIDir 'Ecommerce_Intelligence_OS.Report'
$StaticResDir = Join-Path $ReportFolder 'StaticResources\RegisteredResources'

foreach ($d in @($SmFolder, $ReportFolder)) {
    if (Test-Path $d) { Remove-Item $d -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $SmDefFolder, $StaticResDir | Out-Null

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom)
}

# ==============================================================================
# 1. BUILD TABULAR SEMANTIC MODEL (TOM -> TMDL)
# ==============================================================================
$db = New-Object Microsoft.AnalysisServices.Tabular.Database
$db.Name = 'Ecommerce_Intelligence_OS'
$db.CompatibilityLevel = 1567

$model = New-Object Microsoft.AnalysisServices.Tabular.Model
$model.Culture = 'en-US'
$model.DefaultPowerBIDataSourceVersion = [Microsoft.AnalysisServices.Tabular.PowerBIDataSourceVersion]::PowerBI_V3
$db.Model = $model

function New-MColumnTypeText([string]$ColName, [string]$MType) {
    return "{`"$ColName`", $MType}"
}

function Add-CsvTable {
    param(
        [string]$TableName,
        [string]$CsvPath,
        [array]$Columns,
        [string]$DataCategory = '',
        [string]$KeyColumn = '',
        [string]$ExtraMStep = '',
        [hashtable]$FormatOverrides = @{},
        [hashtable]$SortByOverrides = @{}
    )
    $tbl = New-Object Microsoft.AnalysisServices.Tabular.Table
    $tbl.Name = $TableName
    if ($DataCategory) { $tbl.DataCategory = $DataCategory }

    $mCols = @()
    foreach ($colDef in $Columns) {
        $cName = $colDef[0]
        $tomType = $colDef[1]
        $mType = $colDef[2]
        $isCalculatedInM = ($colDef.Count -ge 4 -and $colDef[3] -eq 'derived')

        $col = New-Object Microsoft.AnalysisServices.Tabular.DataColumn
        $col.Name = $cName
        $col.SourceColumn = $cName
        $col.DataType = [Microsoft.AnalysisServices.Tabular.DataType]::$tomType
        if ($cName -eq $KeyColumn) { $col.IsKey = $true }
        if ($FormatOverrides.ContainsKey($cName)) {
            $col.FormatString = $FormatOverrides[$cName]
        } elseif ($tomType -eq 'DateTime') {
            $col.FormatString = 'yyyy-MM-dd'
        }
        $tbl.Columns.Add($col) | Out-Null

        if (-not $isCalculatedInM) {
            $mCols += (New-MColumnTypeText $cName $mType)
        }
    }

    foreach ($kv in $SortByOverrides.GetEnumerator()) {
        $tbl.Columns[$kv.Key].SortByColumn = $tbl.Columns[$kv.Value]
    }

    $absCsv = (Resolve-Path $CsvPath).Path
    $typeList = $mCols -join ', '
    if ($ExtraMStep) {
        $mExpr = @"
let
    Source = Csv.Document(File.Contents("$absCsv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted,{$typeList}, "en-US"),
    $ExtraMStep
in
    FinalStep
"@
    } else {
        $mExpr = @"
let
    Source = Csv.Document(File.Contents("$absCsv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted,{$typeList}, "en-US")
in
    Typed
"@
    }

    $part = New-Object Microsoft.AnalysisServices.Tabular.Partition
    $part.Name = $TableName
    $part.Mode = [Microsoft.AnalysisServices.Tabular.ModeType]::Import
    $ms = New-Object Microsoft.AnalysisServices.Tabular.MPartitionSource
    $ms.Expression = $mExpr
    $part.Source = $ms
    $tbl.Partitions.Add($part) | Out-Null
    $model.Tables.Add($tbl) | Out-Null
    return $tbl
}

# --- 1A. dim_date (Marked as Date Table) ---
$dimDateExtraM = @'
WithYearLabel = Table.AddColumn(Typed, "year_label", each Text.From([year]), type text),
    FinalStep = Table.AddColumn(WithYearLabel, "analysis_window_label", each if [in_analysis_window] = true then "Jan 2017 - Aug 2018 (D-2 Window)" else "Boundary Months (2016 / Sep-Oct 2018)", type text)
'@
$tblDimDate = Add-CsvTable -TableName 'dim_date' `
    -CsvPath (Join-Path $ExportsDir 'dim_date.csv') `
    -DataCategory 'Time' -KeyColumn 'date_key' `
    -ExtraMStep $dimDateExtraM `
    -Columns @(
        @('date_key',              'DateTime', 'type date'),
        @('year',                  'Int64',    'Int64.Type'),
        @('quarter_num',           'Int64',    'Int64.Type'),
        @('quarter_label',         'String',   'type text'),
        @('month_num',             'Int64',    'Int64.Type'),
        @('year_month',            'String',   'type text'),
        @('month_start_date',      'DateTime', 'type date'),
        @('month_name',            'String',   'type text'),
        @('month_short',           'String',   'type text'),
        @('day_of_month',          'Int64',    'Int64.Type'),
        @('day_of_week_num',       'Int64',    'Int64.Type'),
        @('day_name',              'String',   'type text'),
        @('is_weekend',            'Boolean',  'type logical'),
        @('in_analysis_window',    'Boolean',  'type logical'),
        @('year_label',            'String',   'type text', 'derived'),
        @('analysis_window_label', 'String',   'type text', 'derived')
    ) `
    -SortByOverrides @{
        'year_label'  = 'year'
        'year_month'  = 'month_start_date'
        'month_name'  = 'month_num'
        'month_short' = 'month_start_date'
        'day_name'    = 'day_of_week_num'
    }
foreach ($nonAgg in @('year','quarter_num','month_num','day_of_month','day_of_week_num')) {
    $tblDimDate.Columns[$nonAgg].SummarizeBy = [Microsoft.AnalysisServices.Tabular.AggregateFunction]::None
}

# --- 1B. Granular Star Schema Tables (data/processed/) ---
$tblOrderLevel = Add-CsvTable -TableName 'order_level' `
    -CsvPath (Join-Path $ProcessedDir 'order_level.csv') `
    -KeyColumn 'order_id' `
    -ExtraMStep 'FinalStep = Table.AddColumn(Typed, "PurchaseDate", each if [order_purchase_timestamp] = null then null else Date.From([order_purchase_timestamp]), type date)' `
    -FormatOverrides @{
        'payment_value' = '"R$" #,##0.00'
        'item_revenue'  = '"R$" #,##0.00'
        'freight_value' = '"R$" #,##0.00'
        'delivery_days' = '0.00'
        'review_score'  = '0.00'
        'PurchaseDate'  = 'yyyy-MM-dd'
    } `
    -Columns @(
        @('order_id',                       'String',   'type text'),
        @('customer_id',                    'String',   'type text'),
        @('order_status',                   'String',   'type text'),
        @('order_purchase_timestamp',       'DateTime', 'type datetime'),
        @('order_approved_at',              'DateTime', 'type datetime'),
        @('order_delivered_carrier_date',   'DateTime', 'type datetime'),
        @('order_delivered_customer_date',  'DateTime', 'type datetime'),
        @('order_estimated_delivery_date',  'DateTime', 'type date'),
        @('missing_delivery_date',          'Boolean',  'type logical'),
        @('missing_stage_date',             'Boolean',  'type logical'),
        @('carrier_before_purchase',        'Boolean',  'type logical'),
        @('carrier_before_approval',        'Boolean',  'type logical'),
        @('delivered_before_carrier',       'Boolean',  'type logical'),
        @('status_date_conflict',           'Boolean',  'type logical'),
        @('has_items',                      'Boolean',  'type logical'),
        @('in_analysis_window',             'Boolean',  'type logical'),
        @('delivery_days',                  'Double',   'type number'),
        @('is_late',                        'Boolean',  'type logical'),
        @('is_delivered',                   'Boolean',  'type logical'),
        @('customer_unique_id',             'String',   'type text'),
        @('item_count',                     'Double',   'type number'),
        @('item_revenue',                   'Double',   'type number'),
        @('freight_value',                  'Double',   'type number'),
        @('distinct_products',              'Double',   'type number'),
        @('distinct_sellers',               'Double',   'type number'),
        @('payment_value',                  'Double',   'type number'),
        @('payment_count',                  'Double',   'type number'),
        @('max_installments',               'Double',   'type number'),
        @('review_score',                   'Double',   'type number'),
        @('review_creation_date',           'DateTime', 'type datetime'),
        @('review_answer_timestamp',        'DateTime', 'type datetime'),
        @('review_before_purchase',         'Boolean',  'type logical'),
        @('PurchaseDate',                   'DateTime', 'type date', 'derived')
    )

$tblOrderItems = Add-CsvTable -TableName 'order_items_clean' `
    -CsvPath (Join-Path $ProcessedDir 'order_items_clean.csv') `
    -FormatOverrides @{ 'price' = '"R$" #,##0.00'; 'freight_value' = '"R$" #,##0.00' } `
    -Columns @(
        @('order_id',               'String',   'type text'),
        @('order_item_id',          'Int64',    'Int64.Type'),
        @('product_id',             'String',   'type text'),
        @('seller_id',              'String',   'type text'),
        @('shipping_limit_date',    'DateTime', 'type datetime'),
        @('price',                  'Double',   'type number'),
        @('freight_value',          'Double',   'type number'),
        @('shipping_limit_outlier', 'Boolean',  'type logical'),
        @('missing_category',       'Boolean',  'type logical')
    )

$tblPayments = Add-CsvTable -TableName 'payments_clean' `
    -CsvPath (Join-Path $ProcessedDir 'payments_clean.csv') `
    -FormatOverrides @{ 'payment_value' = '"R$" #,##0.00' } `
    -Columns @(
        @('order_id',             'String',  'type text'),
        @('payment_sequential',   'Int64',   'Int64.Type'),
        @('payment_type',         'String',  'type text'),
        @('payment_installments', 'Int64',   'Int64.Type'),
        @('payment_value',        'Double',  'type number'),
        @('installments_invalid', 'Boolean', 'type logical')
    )

$tblProducts = Add-CsvTable -TableName 'products_clean' `
    -CsvPath (Join-Path $ProcessedDir 'products_clean.csv') `
    -KeyColumn 'product_id' `
    -Columns @(
        @('product_id',                    'String',  'type text'),
        @('product_category_name',         'String',  'type text'),
        @('product_name_lenght',           'Double',  'type number'),
        @('product_description_lenght',    'Double',  'type number'),
        @('product_photos_qty',            'Double',  'type number'),
        @('product_weight_g',              'Double',  'type number'),
        @('product_length_cm',             'Double',  'type number'),
        @('product_height_cm',             'Double',  'type number'),
        @('product_width_cm',              'Double',  'type number'),
        @('product_category_name_english', 'String',  'type text'),
        @('category_name_en',              'String',  'type text'),
        @('missing_dimensions',            'Boolean', 'type logical'),
        @('zero_weight',                   'Boolean', 'type logical')
    )

$tblSellers = Add-CsvTable -TableName 'sellers_clean' `
    -CsvPath (Join-Path $ProcessedDir 'sellers_clean.csv') `
    -KeyColumn 'seller_id' `
    -Columns @(
        @('seller_id',              'String', 'type text'),
        @('seller_zip_code_prefix', 'String', 'type text'),
        @('seller_city',            'String', 'type text'),
        @('seller_state',           'String', 'type text'),
        @('seller_city_normalized', 'String', 'type text')
    )

$tblCustomers = Add-CsvTable -TableName 'customers_clean' `
    -CsvPath (Join-Path $ProcessedDir 'customers_clean.csv') `
    -KeyColumn 'customer_id' `
    -Columns @(
        @('customer_id',              'String', 'type text'),
        @('customer_unique_id',       'String', 'type text'),
        @('customer_zip_code_prefix', 'String', 'type text'),
        @('customer_city',            'String', 'type text'),
        @('customer_state',           'String', 'type text'),
        @('customer_city_normalized', 'String', 'type text')
    )

$tblCustomerRfm = Add-CsvTable -TableName 'customer_rfm' `
    -CsvPath (Join-Path $ProcessedDir 'customer_rfm.csv') `
    -KeyColumn 'customer_unique_id' `
    -FormatOverrides @{ 'monetary' = '"R$" #,##0.00' } `
    -Columns @(
        @('customer_unique_id', 'String', 'type text'),
        @('recency',            'Int64',  'Int64.Type'),
        @('frequency',          'Int64',  'Int64.Type'),
        @('monetary',           'Double', 'type number'),
        @('r_score',            'Int64',  'Int64.Type'),
        @('f_score',            'Int64',  'Int64.Type'),
        @('m_score',            'Int64',  'Int64.Type'),
        @('rfm_score',          'String', 'type text'),
        @('customer_segment',   'String', 'type text')
    )

# --- 1C. Pre-Aggregated Analytical Summary Marts (powerbi/data_exports/) ---
$tblMonthlyKpis = Add-CsvTable -TableName 'pbi_monthly_kpis' `
    -CsvPath (Join-Path $ExportsDir 'pbi_monthly_kpis.csv') `
    -FormatOverrides @{
        'order_value_proxy_brl'      = '"R$" #,##0.00'
        'item_revenue_brl'           = '"R$" #,##0.00'
        'freight_value_brl'          = '"R$" #,##0.00'
        'average_order_value_brl'    = '"R$" #,##0.00'
        'prev_month_order_value_brl' = '"R$" #,##0.00'
        'mom_growth_pct'             = '0.00"%"'
        'avg_delivery_days'          = '0.00'
        'late_delivery_rate_pct'     = '0.00"%"'
        'avg_review_score'           = '0.00'
    } `
    -Columns @(
        @('sales_month',                'String',   'type text'),
        @('month_start_date',           'DateTime', 'type date'),
        @('delivered_orders',           'Int64',    'Int64.Type'),
        @('active_customers',           'Int64',    'Int64.Type'),
        @('order_value_proxy_brl',      'Double',   'type number'),
        @('item_revenue_brl',           'Double',   'type number'),
        @('freight_value_brl',          'Double',   'type number'),
        @('average_order_value_brl',    'Double',   'type number'),
        @('prev_month_order_value_brl', 'Double',   'type number'),
        @('mom_growth_pct',             'Double',   'type number'),
        @('avg_delivery_days',          'Double',   'type number'),
        @('late_delivery_rate_pct',     'Double',   'type number'),
        @('avg_review_score',           'Double',   'type number')
    )

$tblCategoryPerf = Add-CsvTable -TableName 'pbi_category_performance' `
    -CsvPath (Join-Path $ExportsDir 'pbi_category_performance.csv') `
    -FormatOverrides @{
        'item_revenue_brl'       = '"R$" #,##0.00'
        'freight_value_brl'      = '"R$" #,##0.00'
        'avg_item_price_brl'     = '"R$" #,##0.00'
        'avg_delivery_days'      = '0.00'
        'late_delivery_rate_pct' = '0.00"%"'
        'avg_review_score'       = '0.00'
    } `
    -Columns @(
        @('category_name_en',       'String', 'type text'),
        @('category_name_pt',       'String', 'type text'),
        @('delivered_orders',       'Int64',  'Int64.Type'),
        @('items_sold',             'Int64',  'Int64.Type'),
        @('distinct_products',      'Int64',  'Int64.Type'),
        @('distinct_sellers',       'Int64',  'Int64.Type'),
        @('item_revenue_brl',       'Double', 'type number'),
        @('freight_value_brl',      'Double', 'type number'),
        @('avg_item_price_brl',     'Double', 'type number'),
        @('avg_delivery_days',      'Double', 'type number'),
        @('late_delivery_rate_pct', 'Double', 'type number'),
        @('avg_review_score',       'Double', 'type number')
    )

$tblSellerPerf = Add-CsvTable -TableName 'pbi_seller_performance' `
    -CsvPath (Join-Path $ExportsDir 'pbi_seller_performance.csv') `
    -FormatOverrides @{
        'item_revenue_brl'       = '"R$" #,##0.00'
        'freight_value_brl'      = '"R$" #,##0.00'
        'avg_item_price_brl'     = '"R$" #,##0.00'
        'avg_delivery_days'      = '0.00'
        'late_delivery_rate_pct' = '0.00"%"'
        'avg_review_score'       = '0.00'
    } `
    -Columns @(
        @('seller_id',              'String', 'type text'),
        @('seller_state',           'String', 'type text'),
        @('seller_city',            'String', 'type text'),
        @('delivered_orders',       'Int64',  'Int64.Type'),
        @('items_sold',             'Int64',  'Int64.Type'),
        @('distinct_products',      'Int64',  'Int64.Type'),
        @('item_revenue_brl',       'Double', 'type number'),
        @('freight_value_brl',      'Double', 'type number'),
        @('avg_item_price_brl',     'Double', 'type number'),
        @('avg_delivery_days',      'Double', 'type number'),
        @('late_delivery_rate_pct', 'Double', 'type number'),
        @('avg_review_score',       'Double', 'type number')
    )

$tblRfmSummary = Add-CsvTable -TableName 'pbi_rfm_segments_summary' `
    -CsvPath (Join-Path $ExportsDir 'pbi_rfm_segments_summary.csv') `
    -FormatOverrides @{
        'avg_monetary_brl'      = '"R$" #,##0.00'
        'total_order_value_brl' = '"R$" #,##0.00'
        'customer_share_pct'    = '0.00"%"'
        'revenue_share_pct'     = '0.00"%"'
        'avg_recency_days'      = '0.00'
        'avg_purchase_days'     = '0.00'
    } `
    -Columns @(
        @('customer_segment',      'String', 'type text'),
        @('customer_count',        'Int64',  'Int64.Type'),
        @('customer_share_pct',    'Double', 'type number'),
        @('avg_recency_days',      'Double', 'type number'),
        @('avg_purchase_days',     'Double', 'type number'),
        @('avg_monetary_brl',      'Double', 'type number'),
        @('total_order_value_brl', 'Double', 'type number'),
        @('revenue_share_pct',     'Double', 'type number')
    )

$tblStatePerf = Add-CsvTable -TableName 'pbi_state_performance' `
    -CsvPath (Join-Path $ExportsDir 'pbi_state_performance.csv') `
    -FormatOverrides @{
        'order_value_proxy_brl'  = '"R$" #,##0.00'
        'item_revenue_brl'       = '"R$" #,##0.00'
        'freight_value_brl'      = '"R$" #,##0.00'
        'avg_order_value_brl'    = '"R$" #,##0.00'
        'avg_delivery_days'      = '0.00'
        'late_delivery_rate_pct' = '0.00"%"'
        'avg_review_score'       = '0.00'
    } `
    -Columns @(
        @('customer_state',         'String', 'type text'),
        @('delivered_orders',       'Int64',  'Int64.Type'),
        @('unique_customers',       'Int64',  'Int64.Type'),
        @('order_value_proxy_brl',  'Double', 'type number'),
        @('item_revenue_brl',       'Double', 'type number'),
        @('freight_value_brl',      'Double', 'type number'),
        @('avg_order_value_brl',    'Double', 'type number'),
        @('avg_delivery_days',      'Double', 'type number'),
        @('late_delivery_rate_pct', 'Double', 'type number'),
        @('avg_review_score',       'Double', 'type number')
    )

$tblPaymentMethods = Add-CsvTable -TableName 'pbi_payment_methods' `
    -CsvPath (Join-Path $ExportsDir 'pbi_payment_methods.csv') `
    -FormatOverrides @{
        'total_payment_value_brl'   = '"R$" #,##0.00'
        'avg_transaction_value_brl' = '"R$" #,##0.00'
        'avg_installments'          = '0.00'
    } `
    -Columns @(
        @('payment_type',              'String', 'type text'),
        @('transaction_count',         'Int64',  'Int64.Type'),
        @('delivered_orders',          'Int64',  'Int64.Type'),
        @('total_payment_value_brl',   'Double', 'type number'),
        @('avg_transaction_value_brl', 'Double', 'type number'),
        @('avg_installments',          'Double', 'type number')
    )

$tblOrderStatus = Add-CsvTable -TableName 'pbi_order_status_summary' `
    -CsvPath (Join-Path $ExportsDir 'pbi_order_status_summary.csv') `
    -FormatOverrides @{
        'total_payment_value_brl' = '"R$" #,##0.00'
        'total_item_price_brl'    = '"R$" #,##0.00'
        'avg_review_score'        = '0.00'
    } `
    -Columns @(
        @('order_status',            'String', 'type text'),
        @('order_count',             'Int64',  'Int64.Type'),
        @('orders_with_items',       'Double', 'type number'),
        @('total_payment_value_brl', 'Double', 'type number'),
        @('total_item_price_brl',    'Double', 'type number'),
        @('avg_review_score',        'Double', 'type number')
    )

$tblCohortLong = Add-CsvTable -TableName 'pbi_cohort_retention_long' `
    -CsvPath (Join-Path $ExportsDir 'pbi_cohort_retention_long.csv') `
    -FormatOverrides @{
        'cohort_order_value_brl' = '"R$" #,##0.00'
        'retention_rate_pct'     = '0.000"%"'
    } `
    -Columns @(
        @('cohort_month',           'String',   'type text'),
        @('cohort_start_date',      'DateTime', 'type date'),
        @('cohort_size',            'Int64',    'Int64.Type'),
        @('order_month',            'String',   'type text'),
        @('month_index',            'Int64',    'Int64.Type'),
        @('active_customers',       'Int64',    'Int64.Type'),
        @('retention_rate_pct',     'Double',   'type number'),
        @('delivered_orders',       'Int64',    'Int64.Type'),
        @('cohort_order_value_brl', 'Double',   'type number')
    )

# Percentage-point literal format strings (0.279 displays as 0.279%, 100.0 as 100.000%) without modifying underlying values
$tblCohortMatrix = Add-CsvTable -TableName 'pbi_cohort_retention_matrix' `
    -CsvPath (Join-Path $ExportsDir 'pbi_cohort_retention_matrix.csv') `
    -FormatOverrides @{
        'm0_pct' = '0.000"%"'; 'm1_pct' = '0.000"%"'; 'm2_pct' = '0.000"%"'; 'm3_pct' = '0.000"%"'
        'm4_pct' = '0.000"%"'; 'm5_pct' = '0.000"%"'; 'm6_pct' = '0.000"%"'; 'm7_pct' = '0.000"%"'
        'm8_pct' = '0.000"%"'; 'm9_pct' = '0.000"%"'; 'm10_pct'= '0.000"%"'; 'm11_pct'= '0.000"%"'; 'm12_pct' = '0.000"%"'
    } `
    -Columns @(
        @('cohort_month',      'String',   'type text'),
        @('cohort_start_date', 'DateTime', 'type date'),
        @('cohort_size',       'Int64',    'Int64.Type'),
        @('m0_pct', 'Double', 'type number'), @('m1_pct', 'Double', 'type number'),
        @('m2_pct', 'Double', 'type number'), @('m3_pct', 'Double', 'type number'),
        @('m4_pct', 'Double', 'type number'), @('m5_pct', 'Double', 'type number'),
        @('m6_pct', 'Double', 'type number'), @('m7_pct', 'Double', 'type number'),
        @('m8_pct', 'Double', 'type number'), @('m9_pct', 'Double', 'type number'),
        @('m10_pct','Double', 'type number'), @('m11_pct','Double', 'type number'),
        @('m12_pct','Double', 'type number')
    )

$tblDelayBuckets = Add-CsvTable -TableName 'pbi_delivery_delay_buckets' `
    -CsvPath (Join-Path $ExportsDir 'pbi_delivery_delay_buckets.csv') `
    -FormatOverrides @{
        'order_value_proxy_brl'    = '"R$" #,##0.00'
        'avg_actual_delivery_days' = '0.00'
        'avg_days_vs_estimate'     = '0.00'
        'avg_review_score'         = '0.00'
        'order_share_pct'          = '0.00"%"'
        'one_star_share_pct'       = '0.00"%"'
        'five_star_share_pct'      = '0.00"%"'
    } `
    -Columns @(
        @('delivery_timing_bucket',   'String', 'type text'),
        @('delivered_orders',         'Int64',  'Int64.Type'),
        @('order_share_pct',          'Double', 'type number'),
        @('avg_actual_delivery_days', 'Double', 'type number'),
        @('avg_days_vs_estimate',     'Double', 'type number'),
        @('avg_review_score',         'Double', 'type number'),
        @('one_star_share_pct',       'Double', 'type number'),
        @('five_star_share_pct',      'Double', 'type number'),
        @('order_value_proxy_brl',    'Double', 'type number')
    )

$tblClvGroups = Add-CsvTable -TableName 'pbi_customer_clv_groups' `
    -CsvPath (Join-Path $ExportsDir 'pbi_customer_clv_groups.csv') `
    -FormatOverrides @{
        'total_historical_clv_brl' = '"R$" #,##0.00'
        'avg_historical_clv_brl'   = '"R$" #,##0.00'
        'avg_order_value_brl'      = '"R$" #,##0.00'
        'customer_share_pct'       = '0.00"%"'
        'clv_share_pct'            = '0.00"%"'
    } `
    -Columns @(
        @('customer_behaviour_group', 'String', 'type text'),
        @('customer_count',           'Int64',  'Int64.Type'),
        @('customer_share_pct',       'Double', 'type number'),
        @('total_delivered_orders',   'Double', 'type number'),
        @('avg_delivered_orders',     'Double', 'type number'),
        @('avg_lifespan_days',        'Double', 'type number'),
        @('total_historical_clv_brl', 'Double', 'type number'),
        @('clv_share_pct',            'Double', 'type number'),
        @('avg_historical_clv_brl',   'Double', 'type number'),
        @('avg_order_value_brl',      'Double', 'type number')
    )

# ==============================================================================
# 2. CONFIGURE STAR SCHEMA RELATIONSHIPS (Single-Direction Filtering)
# ==============================================================================
function Add-StarRel {
    param(
        [Microsoft.AnalysisServices.Tabular.Table]$FromTbl, [string]$FromCol,
        [Microsoft.AnalysisServices.Tabular.Table]$ToTbl,   [string]$ToCol
    )
    $rel = New-Object Microsoft.AnalysisServices.Tabular.SingleColumnRelationship
    $rel.Name = "rel_$($FromTbl.Name)_$($FromCol)_$($ToTbl.Name)"
    $rel.FromColumn = $FromTbl.Columns[$FromCol]
    $rel.ToColumn   = $ToTbl.Columns[$ToCol]
    $rel.FromCardinality = [Microsoft.AnalysisServices.Tabular.RelationshipEndCardinality]::Many
    $rel.ToCardinality   = [Microsoft.AnalysisServices.Tabular.RelationshipEndCardinality]::One
    $rel.CrossFilteringBehavior = [Microsoft.AnalysisServices.Tabular.CrossFilteringBehavior]::OneDirection
    $rel.IsActive = $true
    $model.Relationships.Add($rel) | Out-Null
}

Add-StarRel $tblOrderLevel   'PurchaseDate'       $tblDimDate     'date_key'
Add-StarRel $tblOrderItems   'order_id'           $tblOrderLevel  'order_id'
Add-StarRel $tblOrderItems   'product_id'         $tblProducts    'product_id'
Add-StarRel $tblOrderItems   'seller_id'          $tblSellers     'seller_id'
Add-StarRel $tblPayments     'order_id'           $tblOrderLevel  'order_id'
Add-StarRel $tblOrderLevel   'customer_id'        $tblCustomers   'customer_id'
Add-StarRel $tblOrderLevel   'customer_unique_id' $tblCustomerRfm 'customer_unique_id'
Add-StarRel $tblMonthlyKpis  'month_start_date'   $tblDimDate     'date_key'
Add-StarRel $tblCohortLong   'cohort_start_date'  $tblDimDate     'date_key'
Add-StarRel $tblCohortMatrix 'cohort_start_date'  $tblDimDate     'date_key'

# ==============================================================================
# 3. ADD ALL APPROVED & WEIGHTED DAX MEASURES
# ==============================================================================
function Add-DaxMeasure {
    param(
        [Microsoft.AnalysisServices.Tabular.Table]$Table,
        [string]$Name,
        [string]$Expr,
        [string]$Format,
        [string]$Folder,
        [string]$Desc = ''
    )
    $m = New-Object Microsoft.AnalysisServices.Tabular.Measure
    $m.Name = $Name
    $m.Expression = $Expr
    $m.FormatString = $Format
    $m.DisplayFolder = $Folder
    if ($Desc) { $m.Description = $Desc }
    $Table.Measures.Add($m) | Out-Null
}

# Section 1: Revenue & Order KPIs (D-1 & D-2)
Add-DaxMeasure $tblOrderLevel 'Delivered Orders' 'CALCULATE(DISTINCTCOUNT(order_level[order_id]), order_level[is_delivered] = TRUE())' '#,##0' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'Total Orders (All Statuses)' 'DISTINCTCOUNT(order_level[order_id])' '#,##0' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'Delivery Completion Rate %' 'DIVIDE([Delivered Orders], [Total Orders (All Statuses)], 0)' '0.00%' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'Delivered Order Value Proxy (BRL)' 'CALCULATE(SUM(order_level[payment_value]), order_level[is_delivered] = TRUE())' '"R$" #,##0.00' '01 Revenue & Orders' 'Approved Rule D-1: Total payment_value on delivered orders (Order Value Proxy, not marketplace commission revenue).'
Add-DaxMeasure $tblOrderItems 'Delivered Item Revenue (BRL)' 'CALCULATE(SUM(order_items_clean[price]), order_level[is_delivered] = TRUE())' '"R$" #,##0.00' '01 Revenue & Orders' 'Approved Rule D-1: SUM(price) for product, category, and seller performance.'
Add-DaxMeasure $tblOrderItems 'Delivered Freight Value (BRL)' 'CALCULATE(SUM(order_items_clean[freight_value]), order_level[is_delivered] = TRUE())' '"R$" #,##0.00' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'Average Order Value (BRL)' 'DIVIDE([Delivered Order Value Proxy (BRL)], [Delivered Orders], 0)' '"R$" #,##0.00' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'Previous Month Order Value Proxy (BRL)' 'CALCULATE([Delivered Order Value Proxy (BRL)], DATEADD(dim_date[date_key], -1, MONTH))' '"R$" #,##0.00' '01 Revenue & Orders'
Add-DaxMeasure $tblOrderLevel 'MoM Order Value Growth %' @"
VAR CurrentVal = [Delivered Order Value Proxy (BRL)]
VAR PrevVal = [Previous Month Order Value Proxy (BRL)]
RETURN
    DIVIDE(CurrentVal - PrevVal, PrevVal, BLANK())
"@ '0.00%' '01 Revenue & Orders'
Add-DaxMeasure $tblPayments 'Payment Transaction Value (BRL)' 'CALCULATE(SUM(payments_clean[payment_value]), order_level[is_delivered] = TRUE())' '"R$" #,##0.00' '01 Revenue & Orders'

# Section 2: Customer Acquisition, Retention, RFM & CLV (D-5 Fixed)
Add-DaxMeasure $tblOrderLevel 'Unique Delivered Customers' 'CALCULATE(DISTINCTCOUNT(order_level[customer_unique_id]), order_level[is_delivered] = TRUE())' '#,##0' '02 Customer & Retention'
Add-DaxMeasure $tblOrderLevel 'Repeat Customers (D-5 Distinct Days)' @"
CALCULATE(
    COUNTROWS(
        FILTER(
            VALUES(order_level[customer_unique_id]),
            CALCULATE(
                DISTINCTCOUNT(order_level[order_id]),
                order_level[is_delivered] = TRUE()
            ) >= 2
            &&
            CALCULATE(
                DISTINCTCOUNT(order_level[PurchaseDate]),
                order_level[is_delivered] = TRUE()
            ) >= 2
        )
    )
)
"@ '#,##0' '02 Customer & Retention' 'Approved Rule D-5: 2+ delivered orders placed on 2+ distinct purchase dates (2,015 / 2.16%).'

Add-DaxMeasure $tblOrderLevel 'Same-Day Multi-Order Customers' @"
CALCULATE(
    COUNTROWS(
        FILTER(
            VALUES(order_level[customer_unique_id]),
            CALCULATE(
                DISTINCTCOUNT(order_level[order_id]),
                order_level[is_delivered] = TRUE()
            ) >= 2
            &&
            CALCULATE(
                DISTINCTCOUNT(order_level[PurchaseDate]),
                order_level[is_delivered] = TRUE()
            ) = 1
        )
    )
)
"@ '#,##0' '02 Customer & Retention' 'Split-basket checkout buyers with 2+ delivered orders on 1 distinct calendar date (786 / 0.84%).'

Add-DaxMeasure $tblOrderLevel 'Any-Day Repeat Customers (Option A)' @"
CALCULATE(
    COUNTROWS(
        FILTER(
            VALUES(order_level[customer_unique_id]),
            CALCULATE(
                DISTINCTCOUNT(order_level[order_id]),
                order_level[is_delivered] = TRUE()
            ) >= 2
        )
    )
)
"@ '#,##0' '02 Customer & Retention' 'Sensitivity benchmark: 2+ delivered orders regardless of purchase date (2,801 / 3.00%).'

Add-DaxMeasure $tblOrderLevel 'Repeat Customer Rate %' 'DIVIDE([Repeat Customers (D-5 Distinct Days)], [Unique Delivered Customers], 0)' '0.00%' '02 Customer & Retention'
Add-DaxMeasure $tblOrderLevel 'Same-Day Multi-Order Rate %' 'DIVIDE([Same-Day Multi-Order Customers], [Unique Delivered Customers], 0)' '0.00%' '02 Customer & Retention'
Add-DaxMeasure $tblOrderLevel 'Historical CLV Proxy per Customer (BRL)' 'DIVIDE([Delivered Order Value Proxy (BRL)], [Unique Delivered Customers], 0)' '"R$" #,##0.00' '02 Customer & Retention'
Add-DaxMeasure $tblRfmSummary 'RFM Customers Count' 'SUM(pbi_rfm_segments_summary[customer_count])' '#,##0' '02 Customer & Retention'
Add-DaxMeasure $tblRfmSummary 'RFM Total Order Value Proxy (BRL)' 'SUM(pbi_rfm_segments_summary[total_order_value_brl])' '"R$" #,##0.00' '02 Customer & Retention'
Add-DaxMeasure $tblRfmSummary 'RFM Weighted Avg Monetary (BRL)' 'DIVIDE(SUM(pbi_rfm_segments_summary[total_order_value_brl]), SUM(pbi_rfm_segments_summary[customer_count]), 0)' '"R$" #,##0.00' '02 Customer & Retention'
Add-DaxMeasure $tblClvGroups  'CLV Weighted Avg Order Value Proxy (BRL)' 'DIVIDE(SUM(pbi_customer_clv_groups[total_historical_clv_brl]), SUM(pbi_customer_clv_groups[customer_count]), 0)' '"R$" #,##0.00' '02 Customer & Retention'
Add-DaxMeasure $tblClvGroups  'CLV Weighted Avg Delivered Orders' 'DIVIDE(SUM(pbi_customer_clv_groups[total_delivered_orders]), SUM(pbi_customer_clv_groups[customer_count]), 0)' '0.00' '02 Customer & Retention'
Add-DaxMeasure $tblCohortLong 'Cohort Retention Rate %' 'DIVIDE(SUM(pbi_cohort_retention_long[active_customers]), SUM(pbi_cohort_retention_long[cohort_size]), BLANK())' '0.00%' '02 Customer & Retention'

# Section 3: Product, Category & Seller Measures
Add-DaxMeasure $tblOrderItems 'Category Item Revenue Share %' 'DIVIDE([Delivered Item Revenue (BRL)], CALCULATE([Delivered Item Revenue (BRL)], ALL(products_clean[category_name_en])), 0)' '0.00%' '03 Product & Seller'
Add-DaxMeasure $tblOrderItems 'Active Delivered Sellers' 'CALCULATE(DISTINCTCOUNT(order_items_clean[seller_id]), order_level[is_delivered] = TRUE())' '#,##0' '03 Product & Seller'
Add-DaxMeasure $tblOrderItems 'Revenue per Active Seller (BRL)' 'DIVIDE([Delivered Item Revenue (BRL)], [Active Delivered Sellers], 0)' '"R$" #,##0.00' '03 Product & Seller'
Add-DaxMeasure $tblCategoryPerf 'Summary Category Weighted Review Score' 'DIVIDE(SUMX(pbi_category_performance, pbi_category_performance[avg_review_score] * pbi_category_performance[delivered_orders]), SUM(pbi_category_performance[delivered_orders]), 0)' '0.00' '03 Product & Seller'
Add-DaxMeasure $tblSellerPerf   'Summary Seller Weighted Late Rate %' 'DIVIDE(SUMX(pbi_seller_performance, (pbi_seller_performance[late_delivery_rate_pct] / 100.0) * pbi_seller_performance[delivered_orders]), SUM(pbi_seller_performance[delivered_orders]), 0)' '0.00%' '03 Product & Seller'
Add-DaxMeasure $tblSellerPerf   'Summary Seller Weighted Review Score' 'DIVIDE(SUMX(pbi_seller_performance, pbi_seller_performance[avg_review_score] * pbi_seller_performance[delivered_orders]), SUM(pbi_seller_performance[delivered_orders]), 0)' '0.00' '03 Product & Seller'

# Section 4: Delivery & Customer Experience (D-3)
Add-DaxMeasure $tblOrderLevel 'Average Delivery Days' 'CALCULATE(AVERAGE(order_level[delivery_days]), order_level[is_delivered] = TRUE(), order_level[missing_delivery_date] = FALSE())' '0.00' '04 Delivery & CX'
Add-DaxMeasure $tblOrderLevel 'Late Delivered Orders' 'CALCULATE(DISTINCTCOUNT(order_level[order_id]), order_level[is_delivered] = TRUE(), order_level[is_late] = TRUE())' '#,##0' '04 Delivery & CX'
Add-DaxMeasure $tblOrderLevel 'Delivered Orders With Delivery Date' 'CALCULATE(DISTINCTCOUNT(order_level[order_id]), order_level[is_delivered] = TRUE(), order_level[missing_delivery_date] = FALSE())' '#,##0' '04 Delivery & CX'
Add-DaxMeasure $tblOrderLevel 'Late Delivery Rate %' 'DIVIDE([Late Delivered Orders], [Delivered Orders With Delivery Date], 0)' '0.00%' '04 Delivery & CX'
Add-DaxMeasure $tblOrderLevel 'On-Time Delivery Rate %' '1.0 - [Late Delivery Rate %]' '0.00%' '04 Delivery & CX'
Add-DaxMeasure $tblOrderLevel 'Average Review Score' 'CALCULATE(AVERAGE(order_level[review_score]), order_level[is_delivered] = TRUE())' '0.00' '04 Delivery & CX' 'Approved Rule D-3: Primary order-level review score uses the most recent review per order.'
Add-DaxMeasure $tblStatePerf    'Summary State Weighted Delivery Days' 'DIVIDE(SUMX(pbi_state_performance, pbi_state_performance[avg_delivery_days] * pbi_state_performance[delivered_orders]), SUM(pbi_state_performance[delivered_orders]), 0)' '0.00' '04 Delivery & CX'
Add-DaxMeasure $tblStatePerf    'Summary State Weighted Late Rate %' 'DIVIDE(SUMX(pbi_state_performance, (pbi_state_performance[late_delivery_rate_pct] / 100.0) * pbi_state_performance[delivered_orders]), SUM(pbi_state_performance[delivered_orders]), 0)' '0.00%' '04 Delivery & CX'
Add-DaxMeasure $tblStatePerf    'Summary State Weighted Review Score' 'DIVIDE(SUMX(pbi_state_performance, pbi_state_performance[avg_review_score] * pbi_state_performance[delivered_orders]), SUM(pbi_state_performance[delivered_orders]), 0)' '0.00' '04 Delivery & CX'
Add-DaxMeasure $tblDelayBuckets 'Delay Bucket Weighted Review Score' 'DIVIDE(SUMX(pbi_delivery_delay_buckets, pbi_delivery_delay_buckets[avg_review_score] * pbi_delivery_delay_buckets[delivered_orders]), SUM(pbi_delivery_delay_buckets[delivered_orders]), 0)' '0.00' '04 Delivery & CX'

# Serialize Semantic Model to TMDL
[Microsoft.AnalysisServices.Tabular.TmdlSerializer]::SerializeDatabaseToFolder($db, $SmDefFolder)
$measCount = ($model.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum
Write-Host "TMDL serialized cleanly: $($model.Tables.Count) tables, $($model.Relationships.Count) relationships, $measCount measures."

Write-Utf8NoBom (Join-Path $SmFolder 'definition.pbism') (@{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json'
    version   = '4.2'
    settings  = @{}
} | ConvertTo-Json -Depth 5)

Write-Utf8NoBom (Join-Path $SmFolder '.platform') (@{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json'
    metadata  = @{ type = 'SemanticModel'; displayName = 'Ecommerce_Intelligence_OS' }
    config    = @{ version = '2.0'; logicalId = 'b41f78c2-119d-4d6e-9f44-6e81239a0001' }
} | ConvertTo-Json -Depth 5)

# ==============================================================================
# 4. BUILD 5-PAGE ENTERPRISE LIGHT REPORT WITH SYNCED SLICER BARS
# ==============================================================================
$ThemeFileName = 'Enterprise_Light_OS_Theme.json'
$themeContent = [System.IO.File]::ReadAllText($ThemeSrc, $Utf8NoBom)
Write-Utf8NoBom (Join-Path $StaticResDir $ThemeFileName) $themeContent

function New-MeasureExpr([string]$Entity, [string]$Prop, [string]$Alias) {
    return @{
        Measure = @{
            Expression = @{ SourceRef = @{ Source = $Alias } }
            Property   = $Prop
        }
        Name = "$Entity.$Prop"
    }
}

function New-ColExpr([string]$Entity, [string]$Prop, [string]$Alias) {
    return @{
        Column = @{
            Expression = @{ SourceRef = @{ Source = $Alias } }
            Property   = $Prop
        }
        Name = "$Entity.$Prop"
    }
}

function New-AggColExpr([string]$Entity, [string]$Prop, [string]$Alias, [int]$Func = 0) {
    return @{
        Aggregation = @{
            Expression = @{
                Column = @{
                    Expression = @{ SourceRef = @{ Source = $Alias } }
                    Property   = $Prop
                }
            }
            Function = $Func
        }
        Name = "Sum($Entity.$Prop)"
    }
}

function New-VisualContainer {
    param(
        [string]$Id, [int]$X, [int]$Y, [int]$W, [int]$H, [int]$Z,
        [string]$VisualType, [string]$Title, [hashtable]$Projections,
        [array]$From, [array]$Select, [array]$OrderBy = @(), [hashtable]$Objects = @{},
        [hashtable]$SyncGroup = $null, [bool]$ShowTitle = $true, [hashtable]$ExtraVcObjects = @{}
    )
    $proto = @{
        Version = 2
        From    = $From
        Select  = $Select
    }
    if ($OrderBy.Count -gt 0) { $proto.OrderBy = $OrderBy }

    if ($ShowTitle) {
        $vcObjs = @{
            title = @(
                @{
                    properties = @{
                        show = @{ expr = @{ Literal = @{ Value = 'true' } } }
                        text = @{ expr = @{ Literal = @{ Value = "'$Title'" } } }
                    }
                }
            )
        }
    } else {
        $vcObjs = @{
            title = @(
                @{
                    properties = @{
                        show = @{ expr = @{ Literal = @{ Value = 'false' } } }
                    }
                }
            )
        }
    }
    foreach ($kv in $ExtraVcObjects.GetEnumerator()) {
        $vcObjs[$kv.Key] = $kv.Value
    }

    $singleVisual = @{
        visualType     = $VisualType
        projections    = $Projections
        prototypeQuery = $proto
        drillFilterOtherVisuals = $true
        vcObjects      = $vcObjs
    }
    if ($Objects.Count -gt 0) { $singleVisual.objects = $Objects }
    if ($null -ne $SyncGroup) { $singleVisual.syncGroup = $SyncGroup }

    $cfgObj = @{
        name    = $Id
        layouts = @(@{ id = 0; position = @{ x = $X; y = $Y; z = $Z; width = $W; height = $H; tabOrder = $Z } })
        singleVisual = $singleVisual
    }

    return @{
        config  = ($cfgObj | ConvertTo-Json -Depth 20 -Compress)
        filters = '[]'
        height  = [double]$H
        width   = [double]$W
        x       = [double]$X
        y       = [double]$Y
        z       = [double]$Z
    }
}

function New-BannerVisual {
    param([string]$Id, [int]$X, [int]$Y, [int]$W, [int]$H, [int]$Z, [string]$Heading, [string]$Subtitle)
    $cfgObj = @{
        name    = $Id
        layouts = @(@{ id = 0; position = @{ x = $X; y = $Y; z = $Z; width = $W; height = $H; tabOrder = $Z } })
        singleVisual = @{
            visualType = 'textbox'
            drillFilterOtherVisuals = $false
            objects = @{
                general = @(
                    @{
                        properties = @{
                            paragraphs = @(
                                @{
                                    textRuns = @(
                                        @{ value = "$Heading   "; textStyle = @{ fontWeight = 'bold'; fontSize = '13pt'; color = '#0F172A' } },
                                        @{ value = $Subtitle; textStyle = @{ fontSize = '9pt'; color = '#475569' } }
                                    )
                                }
                            )
                        }
                    }
                )
            }
        }
    }
    return @{
        config  = ($cfgObj | ConvertTo-Json -Depth 20 -Compress)
        filters = '[]'
        height  = [double]$H
        width   = [double]$W
        x       = [double]$X
        y       = [double]$Y
        z       = [double]$Z
    }
}

function New-KpiCardVisual {
    param([string]$Id, [int]$X, [int]$Y, [int]$W, [int]$H, [int]$Z, [string]$Title, [string]$Entity, [string]$MeasureName)
    return New-VisualContainer -Id $Id -X $X -Y $Y -W $W -H $H -Z $Z -VisualType 'card' -Title $Title `
        -Projections @{ Values = @(@{ queryRef = "$Entity.$MeasureName" }) } `
        -From @(@{ Name = 't'; Entity = $Entity; Type = 0 }) `
        -Select @((New-MeasureExpr $Entity $MeasureName 't'))
}

function New-SyncedSlicerVisual {
    param(
        [string]$Id, [int]$X, [int]$Y, [int]$W, [int]$H, [int]$Z,
        [string]$Title, [string]$Entity, [string]$ColName, [string]$SyncGroupName
    )
    $sg = @{ groupName = $SyncGroupName; fieldChanges = $true; filterChanges = $true }
    $slicerObjects = @{
        data = @(
            @{
                properties = @{
                    mode = @{ expr = @{ Literal = @{ Value = "'Dropdown'" } } }
                }
            }
        )
        general = @(
            @{
                properties = @{
                    orientation = @{ expr = @{ Literal = @{ Value = '0D' } } }
                    responsive  = @{ expr = @{ Literal = @{ Value = 'false' } } }
                }
            }
        )
        header = @(
            @{
                properties = @{
                    show       = @{ expr = @{ Literal = @{ Value = 'true' } } }
                    text       = @{ expr = @{ Literal = @{ Value = "'$Title'" } } }
                    fontColor  = @{ solid = @{ color = @{ expr = @{ Literal = @{ Value = "'#0F172A'" } } } } }
                    fontFamily = @{ expr = @{ Literal = @{ Value = "'Segoe UI Semibold'" } } }
                    textSize   = @{ expr = @{ Literal = @{ Value = '10D' } } }
                    bold       = @{ expr = @{ Literal = @{ Value = 'true' } } }
                }
            }
        )
        items = @(
            @{
                properties = @{
                    fontColor  = @{ solid = @{ color = @{ expr = @{ Literal = @{ Value = "'#0F172A'" } } } } }
                    fontFamily = @{ expr = @{ Literal = @{ Value = "'Segoe UI'" } } }
                    textSize   = @{ expr = @{ Literal = @{ Value = '10D' } } }
                }
            }
        )
        selection = @(
            @{
                properties = @{
                    selectAllCheckboxEnabled = @{ expr = @{ Literal = @{ Value = 'true' } } }
                    singleSelect             = @{ expr = @{ Literal = @{ Value = 'false' } } }
                }
            }
        )
    }
    $extraVc = @{
        padding = @(
            @{
                properties = @{
                    top    = @{ expr = @{ Literal = @{ Value = '2D' } } }
                    bottom = @{ expr = @{ Literal = @{ Value = '2D' } } }
                    left   = @{ expr = @{ Literal = @{ Value = '6D' } } }
                    right  = @{ expr = @{ Literal = @{ Value = '6D' } } }
                }
            }
        )
    }
    return New-VisualContainer -Id $Id -X $X -Y $Y -W $W -H $H -Z $Z -VisualType 'slicer' -Title $Title `
        -ShowTitle $false -ExtraVcObjects $extraVc `
        -Projections @{ Values = @(@{ queryRef = "$Entity.$ColName"; active = $true; displayName = $Title }) } `
        -From @(@{ Name = 't'; Entity = $Entity; Type = 0 }) `
        -Select @((New-ColExpr $Entity $ColName 't')) `
        -Objects $slicerObjects `
        -SyncGroup $sg
}

function New-StandardSlicerBar {
    param([string]$Prefix, [bool]$IncludePayment = $false)
    if ($IncludePayment) {
        return @(
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_yr"  -X 12   -Y 62 -W 152 -H 80 -Z 2 -Title 'Year'             -Entity 'dim_date'        -ColName 'year_label'            -SyncGroupName 'Sync_Date_Year'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_win" -X 174  -Y 62 -W 300 -H 80 -Z 3 -Title 'Analysis Window'  -Entity 'dim_date'        -ColName 'analysis_window_label' -SyncGroupName 'Sync_Window_D2'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_st"  -X 484  -Y 62 -W 216 -H 80 -Z 4 -Title 'Customer State'   -Entity 'customers_clean' -ColName 'customer_state'        -SyncGroupName 'Sync_Customer_State'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_cat" -X 710  -Y 62 -W 310 -H 80 -Z 5 -Title 'Product Category' -Entity 'products_clean'  -ColName 'category_name_en'      -SyncGroupName 'Sync_Product_Category'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_pay" -X 1030 -Y 62 -W 238 -H 80 -Z 6 -Title 'Payment Method'   -Entity 'payments_clean'  -ColName 'payment_type'          -SyncGroupName 'Sync_Payment_Method')
        )
    } else {
        return @(
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_yr"  -X 12  -Y 62 -W 176 -H 80 -Z 2 -Title 'Year'             -Entity 'dim_date'        -ColName 'year_label'            -SyncGroupName 'Sync_Date_Year'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_win" -X 198 -Y 62 -W 366 -H 80 -Z 3 -Title 'Analysis Window'  -Entity 'dim_date'        -ColName 'analysis_window_label' -SyncGroupName 'Sync_Window_D2'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_st"  -X 574 -Y 62 -W 264 -H 80 -Z 4 -Title 'Customer State'   -Entity 'customers_clean' -ColName 'customer_state'        -SyncGroupName 'Sync_Customer_State'),
            (New-SyncedSlicerVisual -Id "${Prefix}_sl_cat" -X 848 -Y 62 -W 420 -H 80 -Z 5 -Title 'Product Category' -Entity 'products_clean'  -ColName 'category_name_en'      -SyncGroupName 'Sync_Product_Category')
        )
    }
}

# --- PAGE 1: Executive Overview ---
$p1Visuals = @(
    (New-BannerVisual -Id 'p1_hdr' -X 12 -Y 8 -W 1256 -H 48 -Z 1 `
        -Heading 'CommerceLens AI — Executive Overview' `
        -Subtitle 'All Dates Default (Use Analysis Window Slicer for Jan 2017 - Aug 2018) | Rule D-5 Repeat: 2.16% (2,015)')
) + (New-StandardSlicerBar -Prefix 'p1') + @(
    (New-KpiCardVisual -Id 'p1_kpi1' -X 12   -Y 148 -W 242 -H 88 -Z 10 -Title 'Delivered Orders'             -Entity 'order_level'       -MeasureName 'Delivered Orders'),
    (New-KpiCardVisual -Id 'p1_kpi2' -X 264  -Y 148 -W 242 -H 88 -Z 11 -Title 'Delivered Order Value Proxy'  -Entity 'order_level'       -MeasureName 'Delivered Order Value Proxy (BRL)'),
    (New-KpiCardVisual -Id 'p1_kpi3' -X 516  -Y 148 -W 242 -H 88 -Z 12 -Title 'Delivered Item Revenue'       -Entity 'order_items_clean' -MeasureName 'Delivered Item Revenue (BRL)'),
    (New-KpiCardVisual -Id 'p1_kpi4' -X 768  -Y 148 -W 242 -H 88 -Z 13 -Title 'Repeat Rate (D-5: 2.16%)'   -Entity 'order_level'       -MeasureName 'Repeat Customer Rate %'),
    (New-KpiCardVisual -Id 'p1_kpi5' -X 1020 -Y 148 -W 248 -H 88 -Z 14 -Title 'Avg Review Score (D-3)'      -Entity 'order_level'       -MeasureName 'Average Review Score'),
    (New-VisualContainer -Id 'p1_ch1' -X 12 -Y 244 -W 620 -H 464 -Z 15 -VisualType 'lineClusteredColumnComboChart' `
        -Title 'Monthly Order Value Proxy (BRL) vs Delivered Orders' `
        -Projections @{
            Category = @(@{ queryRef = 'dim_date.year_month'; active = $true })
            Y        = @(@{ queryRef = 'order_level.Delivered Order Value Proxy (BRL)' })
            Y2       = @(@{ queryRef = 'order_level.Delivered Orders' })
        } `
        -From @(@{ Name = 'd'; Entity = 'dim_date'; Type = 0 }, @{ Name = 'o'; Entity = 'order_level'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'dim_date' 'year_month' 'd'),
            (New-MeasureExpr 'order_level' 'Delivered Order Value Proxy (BRL)' 'o'),
            (New-MeasureExpr 'order_level' 'Delivered Orders' 'o')
        ) `
        -OrderBy @(@{ Direction = 1; Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Source = 'd' } }; Property = 'year_month' } } })),
    (New-VisualContainer -Id 'p1_ch2' -X 644 -Y 244 -W 624 -H 226 -Z 16 -VisualType 'clusteredBarChart' `
        -Title 'Delivered Item Revenue by Product Category (SUM Price)' `
        -Projections @{
            Category = @(@{ queryRef = 'products_clean.category_name_en'; active = $true })
            Y        = @(@{ queryRef = 'order_items_clean.Delivered Item Revenue (BRL)' })
        } `
        -From @(@{ Name = 'p'; Entity = 'products_clean'; Type = 0 }, @{ Name = 'oi'; Entity = 'order_items_clean'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'products_clean' 'category_name_en' 'p'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Item Revenue (BRL)' 'oi')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'oi' } }; Property = 'Delivered Item Revenue (BRL)' } } })),
    (New-VisualContainer -Id 'p1_ch3' -X 644 -Y 480 -W 624 -H 228 -Z 17 -VisualType 'clusteredBarChart' `
        -Title 'Unique Delivered Customers by RFM Segment' `
        -Projections @{
            Category = @(@{ queryRef = 'customer_rfm.customer_segment'; active = $true })
            Y        = @(@{ queryRef = 'order_level.Unique Delivered Customers' })
        } `
        -From @(@{ Name = 'r'; Entity = 'customer_rfm'; Type = 0 }, @{ Name = 'o'; Entity = 'order_level'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'customer_rfm' 'customer_segment' 'r'),
            (New-MeasureExpr 'order_level' 'Unique Delivered Customers' 'o')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'o' } }; Property = 'Unique Delivered Customers' } } }))
)

# --- PAGE 2: Revenue Intelligence ---
$p2Visuals = @(
    (New-BannerVisual -Id 'p2_hdr' -X 12 -Y 8 -W 1256 -H 48 -Z 1 `
        -Heading 'CommerceLens AI — Revenue Intelligence' `
        -Subtitle 'Rule D-1: Delivered Order Value Proxy vs Merchandise Revenue (SUM Price) vs Freight & Payment Mix')
) + (New-StandardSlicerBar -Prefix 'p2' -IncludePayment $true) + @(
    (New-KpiCardVisual -Id 'p2_kpi1' -X 12  -Y 148 -W 304 -H 88 -Z 10 -Title 'Delivered Order Value Proxy'     -Entity 'order_level'       -MeasureName 'Delivered Order Value Proxy (BRL)'),
    (New-KpiCardVisual -Id 'p2_kpi2' -X 328 -Y 148 -W 304 -H 88 -Z 11 -Title 'Delivered Item Revenue (Price)'  -Entity 'order_items_clean' -MeasureName 'Delivered Item Revenue (BRL)'),
    (New-KpiCardVisual -Id 'p2_kpi3' -X 644 -Y 148 -W 304 -H 88 -Z 12 -Title 'Delivered Freight Value'         -Entity 'order_items_clean' -MeasureName 'Delivered Freight Value (BRL)'),
    (New-KpiCardVisual -Id 'p2_kpi4' -X 960 -Y 148 -W 308 -H 88 -Z 13 -Title 'Payment Transaction Value (BRL)' -Entity 'payments_clean'    -MeasureName 'Payment Transaction Value (BRL)'),
    (New-VisualContainer -Id 'p2_ch1' -X 12 -Y 244 -W 748 -H 226 -Z 14 -VisualType 'clusteredColumnChart' `
        -Title 'Monthly Item Revenue vs Freight Value (Responsive to All Slicers)' `
        -Projections @{
            Category = @(@{ queryRef = 'dim_date.year_month'; active = $true })
            Y        = @(@{ queryRef = 'order_items_clean.Delivered Item Revenue (BRL)' }, @{ queryRef = 'order_items_clean.Delivered Freight Value (BRL)' })
        } `
        -From @(@{ Name = 'd'; Entity = 'dim_date'; Type = 0 }, @{ Name = 'oi'; Entity = 'order_items_clean'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'dim_date' 'year_month' 'd'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Item Revenue (BRL)' 'oi'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Freight Value (BRL)' 'oi')
        ) `
        -OrderBy @(@{ Direction = 1; Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Source = 'd' } }; Property = 'year_month' } } })),
    (New-VisualContainer -Id 'p2_ch2' -X 772 -Y 244 -W 496 -H 226 -Z 15 -VisualType 'donutChart' `
        -Title 'Delivered Payment Mix by Payment Method (BRL)' `
        -Projections @{
            Category = @(@{ queryRef = 'payments_clean.payment_type'; active = $true })
            Y        = @(@{ queryRef = 'payments_clean.Payment Transaction Value (BRL)' })
        } `
        -From @(@{ Name = 'pm'; Entity = 'payments_clean'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'payments_clean' 'payment_type' 'pm'),
            (New-MeasureExpr 'payments_clean' 'Payment Transaction Value (BRL)' 'pm')
        )),
    (New-VisualContainer -Id 'p2_tbl1' -X 12 -Y 480 -W 748 -H 228 -Z 16 -VisualType 'tableEx' `
        -Title 'Category Grain Leaderboard (Item Revenue, Freight, Active Sellers & Share)' `
        -Projections @{
            Values = @(
                @{ queryRef = 'products_clean.category_name_en' },
                @{ queryRef = 'order_items_clean.Delivered Item Revenue (BRL)' },
                @{ queryRef = 'order_items_clean.Delivered Freight Value (BRL)' },
                @{ queryRef = 'order_items_clean.Category Item Revenue Share %' },
                @{ queryRef = 'order_items_clean.Active Delivered Sellers' }
            )
        } `
        -From @(@{ Name = 'p'; Entity = 'products_clean'; Type = 0 }, @{ Name = 'oi'; Entity = 'order_items_clean'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'products_clean' 'category_name_en' 'p'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Item Revenue (BRL)' 'oi'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Freight Value (BRL)' 'oi'),
            (New-MeasureExpr 'order_items_clean' 'Category Item Revenue Share %' 'oi'),
            (New-MeasureExpr 'order_items_clean' 'Active Delivered Sellers' 'oi')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'oi' } }; Property = 'Delivered Item Revenue (BRL)' } } })),
    (New-VisualContainer -Id 'p2_ch3' -X 772 -Y 480 -W 496 -H 228 -Z 17 -VisualType 'clusteredBarChart' `
        -Title 'Order Lifecycle Volume by Status (All 99,441 Orders)' `
        -Projections @{
            Category = @(@{ queryRef = 'order_level.order_status'; active = $true })
            Y        = @(@{ queryRef = 'order_level.Total Orders (All Statuses)' })
        } `
        -From @(@{ Name = 'o'; Entity = 'order_level'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'order_level' 'order_status' 'o'),
            (New-MeasureExpr 'order_level' 'Total Orders (All Statuses)' 'o')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'o' } }; Property = 'Total Orders (All Statuses)' } } }))
)

# --- PAGE 3: Customer Intelligence ---
$p3Visuals = @(
    (New-BannerVisual -Id 'p3_hdr' -X 12 -Y 8 -W 1256 -H 48 -Z 1 `
        -Heading 'CommerceLens AI — Customer Intelligence (RFM & CLV)' `
        -Subtitle 'Rule D-5: 2,015 True Repeat (2.16%) | 786 Same-Day Split-Basket (0.84%) | 93,358 Customers')
) + (New-StandardSlicerBar -Prefix 'p3') + @(
    (New-KpiCardVisual -Id 'p3_kpi1' -X 12   -Y 148 -W 242 -H 88 -Z 10 -Title 'Unique Delivered Customers'   -Entity 'order_level' -MeasureName 'Unique Delivered Customers'),
    (New-KpiCardVisual -Id 'p3_kpi2' -X 264  -Y 148 -W 242 -H 88 -Z 11 -Title 'True Repeat (D-5 Distinct Days)' -Entity 'order_level' -MeasureName 'Repeat Customers (D-5 Distinct Days)'),
    (New-KpiCardVisual -Id 'p3_kpi3' -X 516  -Y 148 -W 242 -H 88 -Z 12 -Title 'Same-Day Split-Basket Buyers' -Entity 'order_level' -MeasureName 'Same-Day Multi-Order Customers'),
    (New-KpiCardVisual -Id 'p3_kpi4' -X 768  -Y 148 -W 242 -H 88 -Z 13 -Title 'Repeat Rate (D-5: 2.16%)'   -Entity 'order_level' -MeasureName 'Repeat Customer Rate %'),
    (New-KpiCardVisual -Id 'p3_kpi5' -X 1020 -Y 148 -W 248 -H 88 -Z 14 -Title 'Historical CLV Proxy / Cust'  -Entity 'order_level' -MeasureName 'Historical CLV Proxy per Customer (BRL)'),
    (New-VisualContainer -Id 'p3_ch1' -X 12 -Y 244 -W 620 -H 226 -Z 15 -VisualType 'clusteredBarChart' `
        -Title 'RFM Segment Order Value Proxy (BRL, Filter-Responsive)' `
        -Projections @{
            Category = @(@{ queryRef = 'customer_rfm.customer_segment'; active = $true })
            Y        = @(@{ queryRef = 'order_level.Delivered Order Value Proxy (BRL)' })
        } `
        -From @(@{ Name = 'r'; Entity = 'customer_rfm'; Type = 0 }, @{ Name = 'o'; Entity = 'order_level'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'customer_rfm' 'customer_segment' 'r'),
            (New-MeasureExpr 'order_level' 'Delivered Order Value Proxy (BRL)' 'o')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'o' } }; Property = 'Delivered Order Value Proxy (BRL)' } } })),
    (New-VisualContainer -Id 'p3_ch2' -X 644 -Y 244 -W 624 -H 226 -Z 16 -VisualType 'clusteredColumnChart' `
        -Title 'Weighted Avg Historical CLV Proxy: D-5 Repeat vs Same-Day vs Single' `
        -Projections @{
            Category = @(@{ queryRef = 'pbi_customer_clv_groups.customer_behaviour_group'; active = $true })
            Y        = @(@{ queryRef = 'pbi_customer_clv_groups.CLV Weighted Avg Order Value Proxy (BRL)' })
        } `
        -From @(@{ Name = 'cg'; Entity = 'pbi_customer_clv_groups'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_customer_clv_groups' 'customer_behaviour_group' 'cg'),
            (New-MeasureExpr 'pbi_customer_clv_groups' 'CLV Weighted Avg Order Value Proxy (BRL)' 'cg')
        )),
    (New-VisualContainer -Id 'p3_tbl1' -X 12 -Y 480 -W 620 -H 228 -Z 17 -VisualType 'tableEx' `
        -Title 'RFM Segment Economics (Weighted Avg Monetary & Order Value Totals)' `
        -Projections @{
            Values = @(
                @{ queryRef = 'pbi_rfm_segments_summary.customer_segment' },
                @{ queryRef = 'pbi_rfm_segments_summary.RFM Customers Count' },
                @{ queryRef = 'Sum(pbi_rfm_segments_summary.customer_share_pct)' },
                @{ queryRef = 'pbi_rfm_segments_summary.RFM Weighted Avg Monetary (BRL)' },
                @{ queryRef = 'pbi_rfm_segments_summary.RFM Total Order Value Proxy (BRL)' }
            )
        } `
        -From @(@{ Name = 'r'; Entity = 'pbi_rfm_segments_summary'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_rfm_segments_summary' 'customer_segment' 'r'),
            (New-MeasureExpr 'pbi_rfm_segments_summary' 'RFM Customers Count' 'r'),
            (New-AggColExpr 'pbi_rfm_segments_summary' 'customer_share_pct' 'r' 0),
            (New-MeasureExpr 'pbi_rfm_segments_summary' 'RFM Weighted Avg Monetary (BRL)' 'r'),
            (New-MeasureExpr 'pbi_rfm_segments_summary' 'RFM Total Order Value Proxy (BRL)' 'r')
        )),
    (New-VisualContainer -Id 'p3_tbl2' -X 644 -Y 480 -W 624 -H 228 -Z 18 -VisualType 'tableEx' `
        -Title 'Repeat Behaviour CLV Groups (2,015 D-5 vs 786 Same-Day vs 90,557 Single)' `
        -Projections @{
            Values = @(
                @{ queryRef = 'pbi_customer_clv_groups.customer_behaviour_group' },
                @{ queryRef = 'Sum(pbi_customer_clv_groups.customer_count)' },
                @{ queryRef = 'pbi_customer_clv_groups.CLV Weighted Avg Delivered Orders' },
                @{ queryRef = 'pbi_customer_clv_groups.CLV Weighted Avg Order Value Proxy (BRL)' },
                @{ queryRef = 'Sum(pbi_customer_clv_groups.total_historical_clv_brl)' }
            )
        } `
        -From @(@{ Name = 'cg'; Entity = 'pbi_customer_clv_groups'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_customer_clv_groups' 'customer_behaviour_group' 'cg'),
            (New-AggColExpr 'pbi_customer_clv_groups' 'customer_count' 'cg' 0),
            (New-MeasureExpr 'pbi_customer_clv_groups' 'CLV Weighted Avg Delivered Orders' 'cg'),
            (New-MeasureExpr 'pbi_customer_clv_groups' 'CLV Weighted Avg Order Value Proxy (BRL)' 'cg'),
            (New-AggColExpr 'pbi_customer_clv_groups' 'total_historical_clv_brl' 'cg' 0)
        ))
)

# --- PAGE 4: Product and Seller Performance ---
$p4Visuals = @(
    (New-BannerVisual -Id 'p4_hdr' -X 12 -Y 8 -W 1256 -H 48 -Z 1 `
        -Heading 'CommerceLens AI — Product, Seller & Logistics SLA' `
        -Subtitle 'Seller Item Revenue (SUM Price) vs State Order Value & Delivery Delay Penalty (-1.72 Stars)')
) + (New-StandardSlicerBar -Prefix 'p4') + @(
    (New-KpiCardVisual -Id 'p4_kpi1' -X 12  -Y 148 -W 304 -H 88 -Z 10 -Title 'Active Delivered Sellers' -Entity 'order_items_clean' -MeasureName 'Active Delivered Sellers'),
    (New-KpiCardVisual -Id 'p4_kpi2' -X 328 -Y 148 -W 304 -H 88 -Z 11 -Title 'Average Delivery Days'    -Entity 'order_level'       -MeasureName 'Average Delivery Days'),
    (New-KpiCardVisual -Id 'p4_kpi3' -X 644 -Y 148 -W 304 -H 88 -Z 12 -Title 'Late Delivery Rate %'     -Entity 'order_level'       -MeasureName 'Late Delivery Rate %'),
    (New-KpiCardVisual -Id 'p4_kpi4' -X 960 -Y 148 -W 308 -H 88 -Z 13 -Title 'On-Time Delivery Rate %'  -Entity 'order_level'       -MeasureName 'On-Time Delivery Rate %'),
    (New-VisualContainer -Id 'p4_ch1' -X 12 -Y 244 -W 620 -H 226 -Z 14 -VisualType 'lineClusteredColumnComboChart' `
        -Title 'Delivery Timing Bucket: Delivered Orders vs Weighted Avg Review Score' `
        -Projections @{
            Category = @(@{ queryRef = 'pbi_delivery_delay_buckets.delivery_timing_bucket'; active = $true })
            Y        = @(@{ queryRef = 'Sum(pbi_delivery_delay_buckets.delivered_orders)' })
            Y2       = @(@{ queryRef = 'pbi_delivery_delay_buckets.Delay Bucket Weighted Review Score' })
        } `
        -From @(@{ Name = 'db'; Entity = 'pbi_delivery_delay_buckets'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_delivery_delay_buckets' 'delivery_timing_bucket' 'db'),
            (New-AggColExpr 'pbi_delivery_delay_buckets' 'delivered_orders' 'db' 0),
            (New-MeasureExpr 'pbi_delivery_delay_buckets' 'Delay Bucket Weighted Review Score' 'db')
        ) `
        -OrderBy @(@{ Direction = 1; Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Source = 'db' } }; Property = 'delivery_timing_bucket' } } })),
    (New-VisualContainer -Id 'p4_ch2' -X 644 -Y 244 -W 624 -H 226 -Z 15 -VisualType 'clusteredBarChart' `
        -Title 'Delivered Order Value Proxy by Customer State (Responsive)' `
        -Projections @{
            Category = @(@{ queryRef = 'customers_clean.customer_state'; active = $true })
            Y        = @(@{ queryRef = 'order_level.Delivered Order Value Proxy (BRL)' })
        } `
        -From @(@{ Name = 'c'; Entity = 'customers_clean'; Type = 0 }, @{ Name = 'o'; Entity = 'order_level'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'customers_clean' 'customer_state' 'c'),
            (New-MeasureExpr 'order_level' 'Delivered Order Value Proxy (BRL)' 'o')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'o' } }; Property = 'Delivered Order Value Proxy (BRL)' } } })),
    (New-VisualContainer -Id 'p4_tbl1' -X 12 -Y 480 -W 620 -H 228 -Z 16 -VisualType 'tableEx' `
        -Title 'State Logistics SLA Scorecard (Weighted Delivery Days, Late % & Score)' `
        -Projections @{
            Values = @(
                @{ queryRef = 'pbi_state_performance.customer_state' },
                @{ queryRef = 'Sum(pbi_state_performance.delivered_orders)' },
                @{ queryRef = 'Sum(pbi_state_performance.order_value_proxy_brl)' },
                @{ queryRef = 'pbi_state_performance.Summary State Weighted Delivery Days' },
                @{ queryRef = 'pbi_state_performance.Summary State Weighted Late Rate %' },
                @{ queryRef = 'pbi_state_performance.Summary State Weighted Review Score' }
            )
        } `
        -From @(@{ Name = 'sp'; Entity = 'pbi_state_performance'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_state_performance' 'customer_state' 'sp'),
            (New-AggColExpr 'pbi_state_performance' 'delivered_orders' 'sp' 0),
            (New-AggColExpr 'pbi_state_performance' 'order_value_proxy_brl' 'sp' 0),
            (New-MeasureExpr 'pbi_state_performance' 'Summary State Weighted Delivery Days' 'sp'),
            (New-MeasureExpr 'pbi_state_performance' 'Summary State Weighted Late Rate %' 'sp'),
            (New-MeasureExpr 'pbi_state_performance' 'Summary State Weighted Review Score' 'sp')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Aggregation = @{ Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Source = 'sp' } }; Property = 'delivered_orders' } }; Function = 0 } } })),
    (New-VisualContainer -Id 'p4_tbl2' -X 644 -Y 480 -W 624 -H 228 -Z 17 -VisualType 'tableEx' `
        -Title 'Seller Item Revenue & Delivery Performance (Seller Grain, Filter-Responsive)' `
        -Projections @{
            Values = @(
                @{ queryRef = 'sellers_clean.seller_id' },
                @{ queryRef = 'sellers_clean.seller_state' },
                @{ queryRef = 'order_items_clean.Delivered Item Revenue (BRL)' },
                @{ queryRef = 'order_items_clean.Delivered Freight Value (BRL)' }
            )
        } `
        -From @(@{ Name = 's'; Entity = 'sellers_clean'; Type = 0 }, @{ Name = 'oi'; Entity = 'order_items_clean'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'sellers_clean' 'seller_id' 's'),
            (New-ColExpr 'sellers_clean' 'seller_state' 's'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Item Revenue (BRL)' 'oi'),
            (New-MeasureExpr 'order_items_clean' 'Delivered Freight Value (BRL)' 'oi')
        ) `
        -OrderBy @(@{ Direction = 2; Expression = @{ Measure = @{ Expression = @{ SourceRef = @{ Source = 'oi' } }; Property = 'Delivered Item Revenue (BRL)' } } }))
)

# --- PAGE 5: Retention Analysis ---
$p5Visuals = @(
    (New-BannerVisual -Id 'p5_hdr' -X 12 -Y 8 -W 1256 -H 48 -Z 1 `
        -Heading 'CommerceLens AI — Cohort Retention Analysis' `
        -Subtitle 'Rule D-2 Cohort Window | Weighted Cohort Retention % (M0=100.00%, M1=0.18%-0.72%) | D-5 Repeat: 2.16%')
) + (New-StandardSlicerBar -Prefix 'p5') + @(
    (New-KpiCardVisual -Id 'p5_kpi1' -X 12  -Y 148 -W 304 -H 88 -Z 10 -Title 'Unique Delivered Customers'        -Entity 'order_level' -MeasureName 'Unique Delivered Customers'),
    (New-KpiCardVisual -Id 'p5_kpi2' -X 328 -Y 148 -W 304 -H 88 -Z 11 -Title 'True Repeat (D-5 Distinct Days)'   -Entity 'order_level' -MeasureName 'Repeat Customers (D-5 Distinct Days)'),
    (New-KpiCardVisual -Id 'p5_kpi3' -X 644 -Y 148 -W 304 -H 88 -Z 12 -Title 'Same-Day Split-Basket Buyers'      -Entity 'order_level' -MeasureName 'Same-Day Multi-Order Customers'),
    (New-KpiCardVisual -Id 'p5_kpi4' -X 960 -Y 148 -W 308 -H 88 -Z 13 -Title 'Repeat Rate (D-5: 2.16%)'        -Entity 'order_level' -MeasureName 'Repeat Customer Rate %'),
    (New-VisualContainer -Id 'p5_mtx' -X 12 -Y 244 -W 748 -H 464 -Z 14 -VisualType 'pivotTable' `
        -Title 'Cohort Retention Matrix (% Active = Active Customers / Cohort Size, Weighted %)' `
        -Projections @{
            Rows    = @(@{ queryRef = 'pbi_cohort_retention_long.cohort_month'; active = $true })
            Columns = @(@{ queryRef = 'pbi_cohort_retention_long.month_index'; active = $true })
            Values  = @(@{ queryRef = 'pbi_cohort_retention_long.Cohort Retention Rate %' })
        } `
        -From @(@{ Name = 'cl'; Entity = 'pbi_cohort_retention_long'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_cohort_retention_long' 'cohort_month' 'cl'),
            (New-ColExpr 'pbi_cohort_retention_long' 'month_index' 'cl'),
            (New-MeasureExpr 'pbi_cohort_retention_long' 'Cohort Retention Rate %' 'cl')
        )),
    (New-VisualContainer -Id 'p5_ch1' -X 772 -Y 244 -W 496 -H 226 -Z 15 -VisualType 'clusteredColumnChart' `
        -Title 'Acquired Customer Cohort Size by Month (2017-01 to 2018-08)' `
        -Projections @{
            Category = @(@{ queryRef = 'pbi_cohort_retention_matrix.cohort_month'; active = $true })
            Y        = @(@{ queryRef = 'Sum(pbi_cohort_retention_matrix.cohort_size)' })
        } `
        -From @(@{ Name = 'cm'; Entity = 'pbi_cohort_retention_matrix'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_cohort_retention_matrix' 'cohort_month' 'cm'),
            (New-AggColExpr 'pbi_cohort_retention_matrix' 'cohort_size' 'cm' 0)
        ) `
        -OrderBy @(@{ Direction = 1; Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Source = 'cm' } }; Property = 'cohort_month' } } })),
    (New-VisualContainer -Id 'p5_ch2' -X 772 -Y 480 -W 496 -H 228 -Z 16 -VisualType 'clusteredBarChart' `
        -Title 'Order Value Share % by Repeat Behaviour Group (D-5 vs Same-Day vs Single)' `
        -Projections @{
            Category = @(@{ queryRef = 'pbi_customer_clv_groups.customer_behaviour_group'; active = $true })
            Y        = @(@{ queryRef = 'Sum(pbi_customer_clv_groups.clv_share_pct)' })
        } `
        -From @(@{ Name = 'cg'; Entity = 'pbi_customer_clv_groups'; Type = 0 }) `
        -Select @(
            (New-ColExpr 'pbi_customer_clv_groups' 'customer_behaviour_group' 'cg'),
            (New-AggColExpr 'pbi_customer_clv_groups' 'clv_share_pct' 'cg' 0)
        ))
)

$reportConfigJson = @{
    version = '5.55'
    themeCollection = @{
        baseTheme   = @{ name = 'CY24SU06'; version = '5.55'; type = 2 }
        customTheme = @{ name = $ThemeFileName; reportVersionAtImport = '5.55'; type = 1 }
    }
    activeSectionIndex = 0
    defaultDrillFilterOtherVisuals = $true
} | ConvertTo-Json -Depth 8 -Compress

$reportDocument = @{
    config = $reportConfigJson
    layoutOptimization = 0
    resourcePackages = @(
        @{
            resourcePackage = @{
                disabled = $false
                items = @(
                    @{ name = $ThemeFileName; path = $ThemeFileName; type = 202 }
                )
                name = 'RegisteredResources'
                type = 1
            }
        }
    )
    sections = @(
        @{ config = '{}'; displayName = 'Executive Overview';             displayOption = 1; filters = '[]'; height = 720; name = 'ReportSectionExec';      ordinal = 0; visualContainers = $p1Visuals; width = 1280 },
        @{ config = '{}'; displayName = 'Revenue Intelligence';           displayOption = 1; filters = '[]'; height = 720; name = 'ReportSectionRevenue';   ordinal = 1; visualContainers = $p2Visuals; width = 1280 },
        @{ config = '{}'; displayName = 'Customer Intelligence';          displayOption = 1; filters = '[]'; height = 720; name = 'ReportSectionCustomer';  ordinal = 2; visualContainers = $p3Visuals; width = 1280 },
        @{ config = '{}'; displayName = 'Product and Seller Performance'; displayOption = 1; filters = '[]'; height = 720; name = 'ReportSectionProdSell';  ordinal = 3; visualContainers = $p4Visuals; width = 1280 },
        @{ config = '{}'; displayName = 'Retention Analysis';             displayOption = 1; filters = '[]'; height = 720; name = 'ReportSectionRetention'; ordinal = 4; visualContainers = $p5Visuals; width = 1280 }
    )
}

Write-Utf8NoBom (Join-Path $ReportFolder 'report.json') ($reportDocument | ConvertTo-Json -Depth 25)

Write-Utf8NoBom (Join-Path $ReportFolder 'definition.pbir') (@{
    '$schema'        = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json'
    version          = '4.0'
    datasetReference = @{ byPath = @{ path = '../Ecommerce_Intelligence_OS.SemanticModel' } }
} | ConvertTo-Json -Depth 6)

Write-Utf8NoBom (Join-Path $ReportFolder '.platform') (@{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json'
    metadata  = @{ type = 'Report'; displayName = 'Ecommerce_Intelligence_OS' }
    config    = @{ version = '2.0'; logicalId = 'b41f78c2-119d-4d6e-9f44-6e81239a0002' }
} | ConvertTo-Json -Depth 5)

Write-Utf8NoBom $PbipPath (@{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json'
    version   = '1.0'
    artifacts = @(@{ report = @{ path = 'Ecommerce_Intelligence_OS.Report' } })
    settings  = @{ enableAutoRecovery = $true }
} | ConvertTo-Json -Depth 6)

# ==============================================================================
# 5. VALIDATE VIA MICROSOFT POWER BI SDK (TMDL + PBIProjectShredder)
# ==============================================================================
$roundTripDb = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($SmDefFolder)
$totalMeasures = ($roundTripDb.Model.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum
Write-Host "TMDL Round-Trip Verified: $($roundTripDb.Model.Tables.Count) tables, $($roundTripDb.Model.Relationships.Count) relationships, $totalMeasures DAX measures."

Add-Type -ReferencedAssemblies (Join-Path $PbiBin 'Microsoft.PowerBI.Packaging.dll') @"
using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.PowerBI.Packaging.Project;
using Microsoft.PowerBI.Packaging.Host;

public class LocalProjectReader : IProjectFilesReader {
    public Task<bool> ExistsAsync(string path) { return Task.FromResult(File.Exists(path) || Directory.Exists(path)); }
    public Task<Stream> GetAsync(string path) {
        if (!File.Exists(path)) return Task.FromResult<Stream>(null);
        return Task.FromResult<Stream>(File.OpenRead(path));
    }
    public Task<string[]> GetAllPathsAsync(string path) {
        if (!Directory.Exists(path)) return Task.FromResult(new string[0]);
        return Task.FromResult(Directory.GetFiles(path, "*", SearchOption.AllDirectories));
    }
}
public class DesktopSwitches : IFeatureSwitches {
    public bool FilesWithMandatorySchema { get { return true; } }
    public bool SimplifiedDatasetRefConnectionString { get { return true; } }
    public bool ReadTmdl { get { return true; } }
    public bool ReadEnhancedReportFormat { get { return false; } }
    public bool VerifiedAnswers { get { return true; } }
    public bool NewCopilotFileFormat { get { return true; } }
}
"@

$ctx = New-Object Microsoft.PowerBI.Packaging.Host.HostContext(
    [Microsoft.PowerBI.Packaging.Host.HostApplication]::Desktop,
    (New-Object DesktopSwitches),
    $null
)
$res = [Microsoft.PowerBI.Packaging.Project.PBIProjectShredder]::OpenProjectAsync((New-Object LocalProjectReader), $PbipPath, $ctx).GetAwaiter().GetResult()
$errCount = $res.Item2.Count
Write-Host "PBIProjectShredder Validation Errors: $errCount"
if ($errCount -gt 0) {
    $res.Item2 | ForEach-Object { Write-Error $_.ToString() }
    throw "PBIP validation failed with $errCount errors."
}
Write-Host "SUCCESS: Power BI Project validated cleanly -> $PbipPath"
