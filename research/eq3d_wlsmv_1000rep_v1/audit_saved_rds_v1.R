#!/usr/bin/env Rscript
# READ ONLY: inspect previously saved lavaan RDS objects, NEVER refit or optimize.
suppressPackageStartupMessages({library(lavaan); library(jsonlite)})
stopifnot(as.character(packageVersion("lavaan")) == "0.7.2")
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L)
input <- args[[1L]]
out <- args[[2L]]
dir.create(out, recursive=TRUE, showWarnings=FALSE)

safe <- function(expr) tryCatch(expr, error=function(e) NULL)
as_matrix <- function(x) {
  if (is.list(x) && length(x)==1L) x <- x[[1L]]
  if (is.matrix(x) && is.numeric(x)) x else NULL
}
matrix_diagnostic <- function(x) {
  x <- as_matrix(x)
  if (is.null(x) || nrow(x)!=ncol(x) || any(!is.finite(x)))
    return(list(available=FALSE, dimension=NA_integer_, min_eigen=NA_real_,
                max_eigen=NA_real_, numerical_rank=NA_integer_,
                tolerance=NA_real_, positive_definite=NA))
  vals <- eigen((x+t(x))/2, symmetric=TRUE, only.values=TRUE)$values
  scale <- max(abs(vals), .Machine$double.eps)
  tol <- scale*max(dim(x))*sqrt(.Machine$double.eps)
  list(available=TRUE, dimension=nrow(x), min_eigen=min(vals),
       max_eigen=max(vals), numerical_rank=sum(abs(vals)>tol),
       tolerance=tol, positive_definite=all(vals>tol))
}
get_gradient <- function(fit) {
  x <- safe(lavTech(fit, "gradient"))
  if (is.list(x) && length(x)==1L) x <- x[[1L]]
  if (!is.numeric(x) || !length(x) || !all(is.finite(x)))
    return(list(available=FALSE, components=NA_integer_, max_abs=NA_real_))
  list(available=TRUE, components=length(x), max_abs=max(abs(x)))
}
cases <- expand.grid(truth=c("M4","M5"),
                     model=c("M3","M4","M5","M7"),
                     stringsAsFactors=FALSE)
saved <- read.csv(file.path(input,"PAIRED_FIT_DIAGNOSTIC.csv"),
                  stringsAsFactors=FALSE)
stopifnot(nrow(saved)==8L)
rows <- list()
objects <- list()
for (i in seq_len(nrow(cases))) {
  truth <- cases$truth[[i]]
  model <- cases$model[[i]]
  key <- paste(truth,model,sep="_")
  path <- file.path(input,paste0("fit_",key,".rds"))
  stopifnot(file.exists(path))
  fit <- readRDS(path)
  stopifnot(inherits(fit,"lavaan"))
  previous <- saved[saved$truth==truth & saved$fit_model==model,,drop=FALSE]
  stopifnot(nrow(previous)==1L)
  convergence <- isTRUE(safe(lavInspect(fit,"converged")))
  stopifnot(convergence==previous$converged[[1L]])
  grad <- get_gradient(fit)
  hess <- matrix_diagnostic(safe(lavTech(fit,"hessian")))
  info <- matrix_diagnostic(safe(lavTech(fit,"information")))
  cov_lv <- matrix_diagnostic(safe(lavInspect(fit,"cov.lv")))
  covm <- as_matrix(safe(lavInspect(fit,"cov.lv")))
  if (!is.null(covm))
    write.csv(covm,file.path(out,paste0("covlv_",key,".csv")),
              row.names=TRUE)
  # Existing saved parameter CSV, not a new estimation.
  pars <- read.csv(file.path(input,paste0("params_",key,".csv")))
  stopifnot(nrow(pars)>0L)
  free_se <- sum(is.finite(pars$se) & pars$se>0,na.rm=TRUE)
  row <- data.frame(
    truth=truth, fit_model=model, converged=convergence,
    original_warning_count=previous$warning_count[[1L]],
    original_warning_text=previous$warnings[[1L]],
    gradient_available=grad$available,
    gradient_max_abs=grad$max_abs,
    hessian_available=hess$available,
    hessian_dimension=hess$dimension,
    hessian_rank=hess$numerical_rank,
    hessian_min_eigen=hess$min_eigen,
    information_available=info$available,
    information_dimension=info$dimension,
    information_rank=info$numerical_rank,
    information_min_eigen=info$min_eigen,
    covlv_available=cov_lv$available,
    covlv_dimension=cov_lv$dimension,
    covlv_rank=cov_lv$numerical_rank,
    covlv_min_eigen=cov_lv$min_eigen,
    covlv_positive_definite=cov_lv$positive_definite,
    param_rows=nrow(pars),
    finite_positive_standard_errors=free_se,
    stringsAsFactors=FALSE
  )
  rows[[key]] <- row
  objects[[key]] <- list(gradient=grad,hessian=hess,information=info,covlv=cov_lv)
}
d <- do.call(rbind,rows)
write.csv(d,file.path(out,"RDS_NUMERICAL_DIAGNOSTICS.csv"),row.names=FALSE)
m4 <- d[d$truth=="M4" & d$fit_model=="M3",,drop=FALSE]
m5 <- d[d$truth=="M5" & d$fit_model=="M3",,drop=FALSE]
stopifnot(nrow(d)==8L,nrow(m4)==1L,nrow(m5)==1L)
verdict <- list(
 gate="EQ3D_M4_M5_SAVED_RDS_GRADIENT_COVLV_AND_IDENTIFICATION_AUDIT_V1",
 source_run=41983775160, source_artifact_id=13395326601,
 mode="SAVED_RDS_READ_ONLY_NO_REFIT",
 lavaan_version=as.character(packageVersion("lavaan")),
 inspected_objects=8L,
 m4_to_m3_converged=isTRUE(m4$converged[[1L]]),
 m5_to_m3_converged=isTRUE(m5$converged[[1L]]),
 m4_to_m3_gradient_available=isTRUE(m4$gradient_available[[1L]]),
 m5_to_m3_covlv_available=isTRUE(m5$covlv_available[[1L]]),
 m5_to_m3_covlv_positive_definite=isTRUE(m5$covlv_positive_definite[[1L]]),
 numerical_diagnostics=objects,
 thresholds="Eigen rank tolerance is numerical heuristic, not formal identification proof.",
 verdict="PASS_SAVED_RDS_READBACK__HOLD_NUMERICAL_ADMISSIBILITY_AND_IDENTIFICATION",
 claim_ceiling=c("NO_EMPIRICAL_VALIDATION","NO_GLOBAL_BIND",
                 "NO_PRODUCTION_ADMISSION","NO_SCALED_CHISQUARE_DIFFERENCE_TEST")
)
write_json(verdict,file.path(out,"RDS_AUDIT_RECEIPT.json"),
           pretty=TRUE,auto_unbox=TRUE,na="null",null="null")
cat("PASS_SAVED_RDS_OBJECTS_8_OF_8\n")
cat("M4_M3_CONVERGED=",verdict$m4_to_m3_converged,"\n",sep="")
cat("M5_M3_COVLV_POSITIVE_DEFINITE=",
    verdict$m5_to_m3_covlv_positive_definite,"\n",sep="")
