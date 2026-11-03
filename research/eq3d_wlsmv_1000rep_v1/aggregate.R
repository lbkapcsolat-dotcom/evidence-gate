#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(jsonlite))
source("research/eq3d_wlsmv_1000rep_v1/row_contract.R")
args <- commandArgs(trailingOnly=TRUE)
artifact_root <- args[[1]]
outdir <- args[[2]]
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)

files <- list.files(artifact_root,pattern="grid\\.csv$",recursive=TRUE,full.names=TRUE)
if(length(files) != 48L) stop(sprintf("HOLD_EXPECTED_48_GRID_SHARDS_FOUND_%d",length(files)))
x <- do.call(rbind,lapply(files,read_canonical_grid_csv))
required_N <- c(4800L,6000L,7200L)
required_truth <- c("M3","M4","M5","M7")
cells <- expand.grid(N=required_N,truth=required_truth,stringsAsFactors=FALSE)

wilson <- function(k,n,z=1.959963984540054) {
  p <- k/n
  den <- 1+z^2/n
  ctr <- (p+z^2/(2*n))/den
  half <- z*sqrt(p*(1-p)/n+z^2/(4*n^2))/den
  c(lower=ctr-half,upper=ctr+half)
}

rows <- list()
for(i in seq_len(nrow(cells))) {
  N <- cells$N[i]; truth <- cells$truth[i]
  d <- x[x$N==N & x$truth==truth,]
  if(nrow(d)!=1000L) stop(sprintf("HOLD_CELL_%s_%s_HAS_%d_NOT_1000",N,truth,nrow(d)))
  correct <- if(truth=="M3") (d$status=="OK" & d$m3_support==1) else (d$status=="OK" & d$m3_support==0)
  k <- sum(correct,na.rm=TRUE)
  ci <- wilson(k,1000)
  rows[[i]] <- data.frame(
    N=N,truth=truth,attempts=1000,
    ok=sum(d$status=="OK"),
    failures=sum(d$status!="OK"),
    correct=k,
    decision_rate=k/1000,
    ci95_lower=ci[1],
    ci95_upper=ci[2],
    mean_elapsed_sec=mean(d$elapsed,na.rm=TRUE)
  )
}
summary <- do.call(rbind,rows)
write.csv(summary,file.path(outdir,"CELL_SUMMARY.csv"),row.names=FALSE)

byN <- aggregate(decision_rate~N,data=summary,FUN=min)
names(byN)[2] <- "minimum_two_sided_rate"
byN$pass_90 <- byN$minimum_two_sided_rate >= .90
write.csv(byN,file.path(outdir,"N_SUMMARY.csv"),row.names=FALSE)

sens_files <- list.files(artifact_root,pattern="sensitivity_summary\\.json$",recursive=TRUE,full.names=TRUE)
if(length(sens_files)!=1L) stop(sprintf("HOLD_EXPECTED_1_SENSITIVITY_SUMMARY_FOUND_%d",length(sens_files)))
sens <- fromJSON(sens_files[[1]])

esem_pass <- identical(sens$esem$verdict,"PASS_ESEM_CROSSLOADING_SENSITIVITY")
method_closed <- sens$method_factor$verdict %in% c(
  "PASS_METHOD_FACTOR_DETECTOR",
  "FAIL_METHOD_FACTOR_DETECTOR_POSITIVE_CONTROL"
)
method_path <- if(identical(sens$method_factor$verdict,"PASS_METHOD_FACTOR_DETECTOR")) {
  "METHOD_FACTOR_RETAINED"
} else if(identical(sens$method_factor$verdict,"FAIL_METHOD_FACTOR_DETECTOR_POSITIVE_CONTROL")) {
  "METHOD_FACTOR_REJECTED_AS_UNRELIABLE__ESEM_IS_PRIMARY_SENSITIVITY"
} else {
  "METHOD_FACTOR_UNRESOLVED"
}

passing <- byN$N[byN$pass_90]
grid_complete <- nrow(summary)==12L && all(summary$attempts==1000L)
if(length(passing)>0) {
  locked_analyzable <- min(passing)
  yield <- 1000/1200
  locked_recruited <- ceiling((locked_analyzable/yield)/100)*100
} else {
  locked_analyzable <- NA_integer_
  locked_recruited <- NA_integer_
}

if(grid_complete && esem_pass && method_closed && length(passing)>0) {
  final_verdict <- "PASS_FINAL_RECRUITMENT_LOCK"
} else if(!grid_complete) {
  final_verdict <- "HOLD_GRID_INCOMPLETE"
} else if(!esem_pass) {
  final_verdict <- "HOLD_ESEM_SENSITIVITY"
} else if(!method_closed) {
  final_verdict <- "HOLD_METHOD_FACTOR_CLOSURE"
} else {
  final_verdict <- "HOLD_NO_TESTED_N_REACHES_90_PERCENT"
}

receipt <- list(
  gate="EQUILIBRIUM_CANONICAL_3D_DISTRIBUTED_EXACT_WLSMV_1000_REP_GRID_AND_METHOD_FACTOR_CLOSURE_V1",
  grid=list(
    shards=48,
    cells=12,
    attempts_per_cell=1000,
    total_attempts=nrow(x),
    complete=grid_complete,
    decision_rule="Correct decisions / all 1000 attempts; nonconvergence counts against decision rate.",
    N_summary=byN
  ),
  sensitivity=sens,
  method_factor_closure=list(
    status=sens$method_factor$verdict,
    path=method_path
  ),
  recruitment=list(
    analyzable_N=if(is.na(locked_analyzable)) NULL else locked_analyzable,
    recruited_N=if(is.na(locked_recruited)) NULL else locked_recruited,
    planning_yield=1000/1200,
    rule="Smallest tested analyzable N with minimum decision rate >=0.90, rounded recruited N upward to nearest 100."
  ),
  final_verdict=final_verdict,
  claim_ceiling=c(
    "EXACT_ORDINAL_WLSMV_1000_REP_PER_CELL",
    "NO_EMPIRICAL_HUMAN_3D_VALIDATION",
    "NO_HAKEN_ORDER_PARAMETER_CLAIM",
    "NO_CLINICAL_CLAIM",
    "NO_GLOBAL_BIND",
    "NO_PRODUCTION_ADMISSION"
  )
)
write_json(receipt,file.path(outdir,"FINAL_RECEIPT.json"),pretty=TRUE,auto_unbox=TRUE,na="null")
writeLines(c(
  paste0("FINAL_VERDICT=",final_verdict),
  paste0("LOCKED_ANALYZABLE_N=",ifelse(is.na(locked_analyzable),"NA",locked_analyzable)),
  paste0("LOCKED_RECRUITED_N=",ifelse(is.na(locked_recruited),"NA",locked_recruited)),
  paste0("ESEM=",sens$esem$verdict),
  paste0("METHOD_FACTOR=",sens$method_factor$verdict),
  paste0("METHOD_PATH=",method_path)
),file.path(outdir,"RECRUITMENT_LOCK.txt"))
cat(toJSON(receipt,pretty=TRUE,auto_unbox=TRUE,na="null"),"\n")
