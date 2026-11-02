#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(lavaan)
  library(mvtnorm)
  library(parallel)
})
outdir <- commandArgs(trailingOnly=TRUE)[1]
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
stopifnot(as.character(packageVersion("lavaan")) == "0.7.2")

items <- c(paste0("A",1:5),paste0("V",1:5),paste0("H",1:5),
           paste0("SE",1:6),paste0("FF",1:5),paste0("M",1:4),paste0("C",1:8))
groups <- c(rep("A",5),rep("V",5),rep("H",5),rep("SE",6),rep("FF",5),rep("M",4),rep("C",8))
cats <- c(rep(7,15),rep(4,6),rep(5,5),rep(7,12))
facs <- c("A","V","H","SE","FF","M","C")
loads <- numeric(length(items))
for(g in unique(groups)) { ix<-which(groups==g); loads[ix]<-seq(.64,.80,length.out=length(ix)) }
thr <- list("7"=c(-1.5,-.8,-.3,.2,.8,1.5),"5"=c(-1,-.3,.4,1.1),"4"=c(-.8,.1,.9))
partner <- c(A="V",V="A",H="A",SE="M",FF="C",M="SE",C="FF")
signm <- c(A=1,V=-1,H=1,SE=1,FF=-1,M=1,C=-1)

Ppos <- matrix(c(
  1,.6084,.6084,.273,.273,.234,.234,
  .6084,1,.6084,.273,.273,.234,.234,
  .6084,.6084,1,.273,.273,.234,.234,
  .273,.273,.273,1,.6084,.312,.312,
  .273,.273,.273,.6084,1,.312,.312,
  .234,.234,.234,.312,.312,1,.6084,
  .234,.234,.234,.312,.312,.6084,1),7,7,byrow=TRUE)
D <- diag(c(1,-1,1,1,-1,1,-1))
P3 <- D %*% Ppos %*% D
colnames(P3)<-rownames(P3)<-facs

native <- paste(
  'A =~',paste(paste0('A',1:5),collapse='+'),
  '\nV =~',paste(paste0('V',1:5),collapse='+'),
  '\nH =~',paste(paste0('H',1:5),collapse='+'),
  '\nSE =~',paste(paste0('SE',1:6),collapse='+'),
  '\nFF =~',paste(paste0('FF',1:5),collapse='+'),
  '\nM =~',paste(paste0('M',1:4),collapse='+'),
  '\nC =~',paste(paste0('C',1:8),collapse='+'))
m3 <- paste(native,'\nTUD =~ A + V + H\nEMO =~ SE + FF\nBODY =~ M + C\nTUD ~~ EMO + BODY\nEMO ~~ BODY')

sim <- function(N,seed,cross=.0,method=.0,df=6) {
  set.seed(seed)
  F <- rmvt(N,sigma=P3,df=df,type="shifted")
  F <- scale(F)
  style <- rnorm(N)
  X <- matrix(NA_integer_,N,length(items))
  for(j in seq_along(items)) {
    g <- groups[j]; k <- match(g,facs); kp <- match(partner[g],facs)
    signal <- loads[j]*F[,k] + cross*F[,kp] + method*signm[g]*style
    ev <- max(1-loads[j]^2-cross^2-method^2,.05)
    y <- signal + sqrt(ev)*rnorm(N)
    X[,j] <- findInterval(y,thr[[as.character(cats[j])]])+1L
  }
  d <- as.data.frame(X); names(d)<-items
  for(nm in names(d)) d[[nm]] <- ordered(d[[nm]])
  d
}

esem_one <- function(i) {
  d <- sim(6000,3100000+i,cross=.04,method=0)
  f3 <- try(cfa(m3,data=d,ordered=items,estimator="WLSMV",std.lv=TRUE,parameterization="theta"),silent=TRUE)
  fe <- try(efa(data=d,nfactors=7,ordered=items,estimator="WLSMV",rotation="geomin",output="lavaan"),silent=TRUE)
  if(inherits(f3,"try-error") || inherits(fe,"try-error"))
    return(data.frame(rep=i,status="FAIL"))
  a <- fitMeasures(f3,c("cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  b <- fitMeasures(fe,c("cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  data.frame(rep=i,status="OK",
    strict_cfi=a[1],strict_tli=a[2],strict_rmsea=a[3],strict_srmr=a[4],
    esem_cfi=b[1],esem_tli=b[2],esem_rmsea=b[3],esem_srmr=b[4],
    delta_srmr=a[4]-b[4])
}

method_one <- function(i) {
  d <- sim(6000,4100000+i,cross=0,method=.20)
  neg <- c(paste0("V",1:5),paste0("FF",1:5),paste0("C",1:8))
  for(nm in neg) {
    K <- nlevels(d[[nm]])
    x <- as.integer(d[[nm]])
    d[[nm]] <- ordered(K+1L-x,levels=seq_len(K))
  }
  native2 <- paste(
    'A =~',paste(paste0('A',1:5),collapse='+'),
    '\nV =~',paste(paste0('V',1:5),collapse='+'),
    '\nH =~',paste(paste0('H',1:5),collapse='+'),
    '\nSE =~',paste(paste0('SE',1:6),collapse='+'),
    '\nFF =~',paste(paste0('FF',1:5),collapse='+'),
    '\nM =~',paste(paste0('M',1:4),collapse='+'),
    '\nC =~',paste(paste0('C',1:8),collapse='+'))
  ri <- paste0('RI =~ ',paste(paste0('1*',items),collapse=' + '))
  orth <- 'RI ~~ 0*A + 0*V + 0*H + 0*SE + 0*FF + 0*M + 0*C'
  model <- paste(native2,ri,orth,sep='\n')
  fit <- try(cfa(model,data=d,ordered=items,estimator="WLSMV",std.lv=FALSE,parameterization="theta"),silent=TRUE)
  if(inherits(fit,"try-error")) return(data.frame(rep=i,status="FAIL"))
  conv <- lavInspect(fit,"converged")
  pe <- parameterEstimates(fit,standardized=TRUE)
  z <- pe[pe$lhs=="RI" & pe$op=="~~" & pe$rhs=="RI",]
  if(nrow(z)!=1) return(data.frame(rep=i,status="NO_RI_VAR",converged=conv))
  detected <- isTRUE(conv) && is.finite(z$est) && is.finite(z$pvalue) && z$est > .02 && z$pvalue < .05
  data.frame(rep=i,status="OK",converged=conv,ri_var=z$est,ri_p=z$pvalue,detected=as.integer(detected))
}

cores <- min(2L,detectCores())
es <- do.call(rbind,mclapply(1:50,esem_one,mc.cores=cores,mc.preschedule=FALSE))
me <- do.call(rbind,mclapply(1:20,method_one,mc.cores=cores,mc.preschedule=FALSE))
write.csv(es,file.path(outdir,"esem_50rep.csv"),row.names=FALSE)
write.csv(me,file.path(outdir,"method_positive_control_20rep.csv"),row.names=FALSE)

es_ok <- es[es$status=="OK",]
me_ok <- me[me$status=="OK",]
summary <- list(
  lavaan=as.character(packageVersion("lavaan")),
  esem=list(
    total=nrow(es),ok=nrow(es_ok),
    convergence_rate=nrow(es_ok)/nrow(es),
    median_delta_srmr=if(nrow(es_ok)) median(es_ok$delta_srmr) else NA_real_,
    median_esem_cfi=if(nrow(es_ok)) median(es_ok$esem_cfi) else NA_real_,
    median_esem_rmsea=if(nrow(es_ok)) median(es_ok$esem_rmsea) else NA_real_,
    verdict=if(nrow(es_ok)/nrow(es)>=.95 && median(es_ok$delta_srmr)>=.002) "PASS_ESEM_CROSSLOADING_SENSITIVITY" else "HOLD_ESEM_SENSITIVITY"
  ),
  method_factor=list(
    total=nrow(me),ok=nrow(me_ok),
    detection_rate=if(nrow(me_ok)) mean(me_ok$detected) else 0,
    criterion=".20 injected method effect; PASS detector requires >=.80 detection rate",
    verdict=if(nrow(me_ok) && mean(me_ok$detected)>=.80) "PASS_METHOD_FACTOR_DETECTOR" else "FAIL_METHOD_FACTOR_DETECTOR_POSITIVE_CONTROL"
  )
)
json <- jsonlite::toJSON(summary,pretty=TRUE,auto_unbox=TRUE,na="null")
writeLines(json,file.path(outdir,"sensitivity_summary.json"))
cat(json,"\n")
