#!/usr/bin/env Rscript
# Bounded diagnostic fixture only: 2 deterministic datasets x 4 fits. Not a new grid.
suppressPackageStartupMessages({
  library(lavaan)
  library(mvtnorm)
  library(jsonlite)
})
stopifnot(as.character(packageVersion("lavaan")) == "0.7.2")
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==1L)
outdir <- args[[1]]
dir.create(outdir, recursive=TRUE, showWarnings=FALSE)
src <- "research/eq3d_wlsmv_1000rep_v1/grid.R"
lines <- readLines(src, warn=FALSE)
start <- grep("^items <- ", lines)
end <- grep("^one_rep <- function", lines)
stopifnot(length(start)==1L, length(end)==1L, end>start)
# Execute only the EXACT source definitions of the preexisting generator/models.
# In particular: not one_rep(), mclapply(), or the 12,000-grid entrypoint.
eval(parse(text=paste(lines[start:(end-1L)],collapse="\n")), envir=.GlobalEnv)
stopifnot(all(c("M3","M4","M5","M7") %in% names(mods)))
Nfixture <- 480L
cases <- c("M4","M5")
fit_names <- c("M3","M4","M5","M7")
records <- list()
failures <- list()
get_measure <- function(fit, key) {
  tryCatch(as.numeric(fitMeasures(fit, key)[[1L]]),
           error=function(e) NA_real_)
}
safe_eigen_min <- function(x) {
  tryCatch(min(eigen(x, symmetric=TRUE, only.values=TRUE)$values),
           error=function(e) NA_real_)
}
for (truth in cases) {
  seed <- as.integer(260611020L + Nfixture*10000L +
    match(truth, c("M3","M4","M5","M7"))*1000000L + 1L)
  data <- simdat(Nfixture, truth_phi[[truth]], seed)
  stopifnot(nrow(data)==Nfixture, ncol(data)==length(items),
            all(vapply(data, is.ordered, logical(1))))
  dfile <- file.path(outdir, paste0("data_",truth,".csv"))
  write.csv(data, dfile, row.names=FALSE)
  st <- tryCatch(make_stats(data), error=function(e)e)
  if (inherits(st,"error")) {
    failures[[truth]] <- conditionMessage(st)
    next
  }
  for (model in fit_names) {
    key <- paste(truth,model,sep="_")
    warnings <- character()
    attempt <- tryCatch(withCallingHandlers(
      cfa(mods[[model]], sample.cov=st$ss$cov,
          sample.mean=setNames(rep(0,length(items)),items),
          sample.th=st$TH, sample.nobs=Nfixture,
          ordered=items, estimator="WLSMV", std.lv=TRUE,
          parameterization="theta", wls.v=st$W, nacov=st$G),
      warning=function(w) {warnings <<- c(warnings,conditionMessage(w));
                           invokeRestart("muffleWarning")}),
      error=function(e)e)
    fit_error <- if(inherits(attempt,"error")) conditionMessage(attempt) else ""
    converged <- if(fit_error=="") tryCatch(isTRUE(lavInspect(attempt,"converged")),
                                         error=function(e)FALSE) else FALSE
    num_parameters <- NA_integer_
    finite_se_fraction <- NA_real_
    vcov_min_eigen <- NA_real_
    if (fit_error=="") {
      rds_path <- file.path(outdir,paste0("fit_",key,".rds"))
      saveRDS(attempt,rds_path,compress="gzip")
      pars <- tryCatch(parameterEstimates(attempt),error=function(e)NULL)
      if(!is.null(pars)) {
        write.csv(pars,file.path(outdir,paste0("params_",key,".csv")),
                  row.names=FALSE)
        num_parameters <- nrow(pars)
        finite_se_fraction <- if("se" %in% names(pars))
          mean(is.finite(pars$se)) else NA_real_
      }
      v <- tryCatch(lavInspect(attempt,"vcov"),error=function(e)NULL)
      if(!is.null(v)) vcov_min_eigen <- safe_eigen_min(v)
    }
    metrics <- c("chisq.scaled","df","cfi.scaled","tli.scaled",
                 "rmsea.scaled","srmr")
    values <- if(fit_error=="") setNames(vapply(metrics,
      function(m)get_measure(attempt,m),numeric(1)),metrics) else
      setNames(rep(NA_real_,length(metrics)),metrics)
    records[[key]] <- data.frame(
      truth=truth,fit_model=model,N=Nfixture,seed=seed,
      converged=converged,error=fit_error,
      warning_count=length(warnings),warnings=paste(unique(warnings),collapse=" | "),
      parameter_rows=num_parameters,finite_se_fraction=finite_se_fraction,
      vcov_min_eigen=vcov_min_eigen,
      chisq_scaled=values[["chisq.scaled"]],df=values[["df"]],
      cfi_scaled=values[["cfi.scaled"]],tli_scaled=values[["tli.scaled"]],
      rmsea_scaled=values[["rmsea.scaled"]],srmr=values[["srmr"]],
      stringsAsFactors=FALSE
    )
  }
}
stopifnot(length(records)==8L, length(failures)==0L)
results <- do.call(rbind,records)
write.csv(results,file.path(outdir,"PAIRED_FIT_DIAGNOSTIC.csv"),row.names=FALSE)
status <- list(
  gate="EQ3D_M4_M5_BOUNDED_LAVAAN_FIT_OBJECT_AND_IDENTIFIABILITY_FIXTURE_V1",
  purpose="Descriptive fit and identifiability probe, not validated model selection",
  source_file=src,source_definition_range=c(start,end-1L),
  source_commit="d4efbe16e4124b332c4f20aa2dc548a299983cfa",
  lavaan_version=as.character(packageVersion("lavaan")),
  N_per_truth=Nfixture,truth_models=cases,fit_models=fit_names,
  total_datasets=2L,total_fits=nrow(results),
  converged_fits=sum(results$converged),
  failed_fits=sum(!results$converged),
  status=if(all(results$converged)) "PASS_BOUNDED_FIT_EXECUTION" else "HOLD_FIT_WARNINGS_OR_NONCONVERGENCE",
  claim_ceiling=c("NO_EMPIRICAL_VALIDATION","NO_GLOBAL_BIND",
                  "NO_PRODUCTION_ADMISSION","NO_FINAL_MODEL_DISCRIMINATION_CLAIM")
)
write_json(status,file.path(outdir,"FIXTURE_RECEIPT.json"),pretty=TRUE,auto_unbox=TRUE)
print(status)
cat("FIXTURE_FITS=",nrow(results)," CONVERGED=",sum(results$converged),"\n",sep="")
