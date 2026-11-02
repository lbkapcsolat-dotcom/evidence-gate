#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(lavaan)
  library(mvtnorm)
  library(jsonlite)
})

set.seed(26061103)

items <- c(paste0("A",1:5),paste0("V",1:5),paste0("H",1:5),
           paste0("SE",1:6),paste0("FF",1:5),paste0("M",1:4),paste0("C",1:8))
groups <- c(rep("A",5),rep("V",5),rep("H",5),rep("SE",6),rep("FF",5),rep("M",4),rep("C",8))
cats <- c(rep(7,15),rep(4,6),rep(5,5),rep(7,12))
facs <- c("A","V","H","SE","FF","M","C")
loads <- numeric(length(items))
for(g in unique(groups)){
  ix <- which(groups==g)
  loads[ix] <- seq(.64,.80,length.out=length(ix))
}
thr <- list("7"=c(-1.5,-.8,-.3,.2,.8,1.5),"5"=c(-1,-.3,.4,1.1),"4"=c(-.8,.1,.9))

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

partner <- c(A='V',V='A',H='A',SE='M',FF='C',M='SE',C='FF')
signm <- c(A=1,V=-1,H=1,SE=1,FF=-1,M=1,C=-1)

simulate_data <- function(N,cross_loading=0,method_loading=0,df=8,seed=1){
  set.seed(seed)
  F <- rmvt(N,sigma=P3,df=df,type="shifted")
  F <- scale(F)
  method <- rnorm(N)
  X <- matrix(NA_integer_,N,length(items))
  for(j in seq_along(items)){
    g <- groups[j]
    k <- match(g,facs)
    kp <- match(partner[g],facs)
    cl <- cross_loading
    ml <- method_loading*signm[g]
    errv <- max(1-loads[j]^2-cl^2-method_loading^2,.05)
    y <- loads[j]*F[,k] + cl*F[,kp] + ml*method + sqrt(errv)*rnorm(N)
    X[,j] <- findInterval(y,thr[[as.character(cats[j])]])+1L
  }
  d <- as.data.frame(X)
  names(d)<-items
  for(nm in names(d)) d[[nm]]<-ordered(d[[nm]])
  d
}

fit_esem <- function(d){
  fit <- efa(data=d,nfactors=7,ordered=items,estimator="WLSMV",rotation="geomin",output="lavaan")
  fm <- fitMeasures(fit,c("cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  list(
    converged=isTRUE(lavInspect(fit,"converged")),
    cfi_scaled=unname(fm["cfi.scaled"]),
    tli_scaled=unname(fm["tli.scaled"]),
    rmsea_scaled=unname(fm["rmsea.scaled"]),
    srmr=unname(fm["srmr"])
  )
}

fit_strict_m3 <- function(d){
  fit <- cfa(m3,data=d,ordered=items,estimator="WLSMV",std.lv=TRUE,parameterization="theta")
  fm <- fitMeasures(fit,c("cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  list(
    converged=isTRUE(lavInspect(fit,"converged")),
    cfi_scaled=unname(fm["cfi.scaled"]),
    tli_scaled=unname(fm["tli.scaled"]),
    rmsea_scaled=unname(fm["rmsea.scaled"]),
    srmr=unname(fm["srmr"])
  )
}

fit_ri_detector <- function(d){
  for(nm in c(paste0('V',1:5),paste0('FF',1:5),paste0('C',1:8))){
    K <- nlevels(d[[nm]])
    x <- as.integer(d[[nm]])
    d[[nm]] <- ordered(K + 1L - x, levels=seq_len(K))
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
  fit <- cfa(model,data=d,ordered=items,estimator="WLSMV",std.lv=FALSE,parameterization="theta")
  pe <- parameterEstimates(fit,standardized=TRUE)
  row <- pe[pe$lhs=="RI" & pe$op=="~~" & pe$rhs=="RI",][1,]
  fm <- fitMeasures(fit,c("cfi.scaled","rmsea.scaled","srmr"))
  list(
    converged=isTRUE(lavInspect(fit,"converged")),
    variance=unname(row$est),
    se=unname(row$se),
    pvalue=unname(row$pvalue),
    cfi_scaled=unname(fm["cfi.scaled"]),
    rmsea_scaled=unname(fm["rmsea.scaled"]),
    srmr=unname(fm["srmr"])
  )
}

clean <- simulate_data(6000,0,0,8,26061103)
stress <- simulate_data(6000,.04,.08,6,26061104)
positive <- simulate_data(6000,0,.20,6,26061105)

clean_esem <- fit_esem(clean)
stress_m3 <- fit_strict_m3(stress)
stress_esem <- fit_esem(stress)
ri_positive <- fit_ri_detector(positive)

method_detector_pass <- isTRUE(ri_positive$converged) &&
                        is.finite(ri_positive$variance) &&
                        ri_positive$variance > .01 &&
                        is.finite(ri_positive$pvalue) &&
                        ri_positive$pvalue < .05

esem_pass <- isTRUE(clean_esem$converged) &&
             isTRUE(stress_esem$converged) &&
             stress_esem$srmr < stress_m3$srmr

receipt <- list(
  clean_esem=clean_esem,
  stress_strict_m3=stress_m3,
  stress_esem=stress_esem,
  method_detector_positive_control=ri_positive,
  esem_crossloading_sensitivity=if(esem_pass) "PASS" else "HOLD",
  method_factor_detector=if(method_detector_pass) "PASS" else "FAIL_POSITIVE_CONTROL",
  closure_rule=if(method_detector_pass) "METHOD_FACTOR_AVAILABLE" else "REJECT_METHOD_FACTOR_DETECTOR_USE_ESEM_SENSITIVITY"
)

write_json(receipt,"sensitivity_receipt.json",pretty=TRUE,auto_unbox=TRUE,digits=10)
cat(toJSON(receipt,pretty=TRUE,auto_unbox=TRUE,digits=10),"\n")
