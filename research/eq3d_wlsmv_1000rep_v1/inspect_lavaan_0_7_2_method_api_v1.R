#!/usr/bin/env Rscript
# READ-ONLY API inspection: NO cfa, NO estimation, NO Monte Carlo, NO p-values.
suppressPackageStartupMessages({library(lavaan);library(jsonlite)})
stopifnot(as.character(packageVersion("lavaan"))=="0.7.2")
args<-commandArgs(trailingOnly=TRUE);stopifnot(length(args)==1L)
dir.create(args[[1]],recursive=TRUE,showWarnings=FALSE)
f<-get("lavTestLRT",asNamespace("lavaan"))
formals_now<-names(formals(f))
mandatory<-c("object","...","method","test","a_method","scaled_shifted","type","model_names")
stopifnot(all(mandatory %in% formals_now))
doc<-tryCatch(capture.output(utils::help("lavTestLRT",package="lavaan")),
error=function(e)character())
out<-list(
 gate="EQ3D_VERSIONED_LAVAAN_0_7_2_METHOD_SURFACE",
 version=as.character(packageVersion("lavaan")),
 function_name="lavTestLRT",
 installed_function_formal_arguments=formals_now,
 a_method_arg_supported="a_method" %in% formals_now,
 scaled_shifted_arg_supported="scaled_shifted" %in% formals_now,
 check_nested_arg_supported="check_nested" %in% formals_now,
 allowed_to_claim_valid_difference_test=FALSE,
 nesting_proven_for_M3_M4_M5_M7=FALSE,
 actual_difference_test_executed=FALSE,
 models_refitted=FALSE,
 reason="API availability does not prove nestedness, regularity, robust test compatibility, positive-definite covariance, or reliable inference.",
 verdict="PASS_VERSIONED_API_SURFACE__HOLD_PAIRWISE_METHOD_ADMISSION",
 claim_ceiling=c("NO_EMPIRICAL_VALIDATION","NO_GLOBAL_BIND",
                 "NO_PRODUCTION_ADMISSION","NO_PROSPECTIVE_EXECUTION"))
write_json(out,file.path(args[[1]],"VERSIONED_LAVAAN_METHOD_SURFACE.json"),
 pretty=TRUE,auto_unbox=TRUE)
cat("PASS_LAVAAN_0_7_2_VERSIONED_API_SURFACE\n")
cat("FORMALS=",paste(formals_now,collapse=","),"\n")
