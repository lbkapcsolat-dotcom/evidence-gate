#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(lavaan)
  library(mvtnorm)
  library(parallel)
})

N <- as.integer(Sys.getenv("GRID_N"))
TRUTH <- Sys.getenv("GRID_TRUTH")
SHARD <- as.integer(Sys.getenv("GRID_SHARD"))
REPS <- as.integer(Sys.getenv("GRID_REPS", "250"))
OUT <- Sys.getenv("GRID_OUT", "result.csv")
STOPIFNOT <- function(x,msg) if(!isTRUE(x)) stop(msg)
STOPIFNOT(N %in% c(4800L,6000L,7200L),"bad N")
STOPIFNOT(TRUTH %in% c("M3","M4","M5","M7"),"bad truth")
STOPIFNOT(SHARD >= 1L && SHARD <= 4L,"bad shard")

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
thr <- list(
  "7"=c(-1.50,-0.80,-0.30,0.20,0.80,1.50),
  "5"=c(-1.00,-0.30,0.40,1.10),
  "4"=c(-0.80,0.10,0.90)
)

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
colnames(P3) <- rownames(P3) <- facs

P4 <- diag(7); colnames(P4)<-rownames(P4)<-facs
for(a in c("A","V","H")) for(b in c("A","V","H")) if(a!=b) P4[a,b]<-.61
P4["M","C"]<-P4["C","M"]<-.61
for(g in c("A","V","H")){
  P4[g,"SE"]<-P4["SE",g]<-.45
  P4[g,"FF"]<-P4["FF",g]<-0
  P4[g,"M"]<-P4["M",g]<-.25
  P4[g,"C"]<-P4["C",g]<-.25
}
P4["SE","FF"]<-P4["FF","SE"]<-0
P4["SE","M"]<-P4["M","SE"]<-.40
P4["SE","C"]<-P4["C","SE"]<-.40

P5 <- diag(7); colnames(P5)<-rownames(P5)<-facs
for(a in c("A","V","H")) for(b in c("A","V","H")) if(a!=b) P5[a,b]<-.61
pairs <- list(c("SE","FF",.15),c("M","C",.18),c("SE","M",.35),
              c("SE","C",.25),c("FF","M",.12),c("FF","C",.20))
for(z in pairs){a<-z[1];b<-z[2];r<-as.numeric(z[3]);P5[a,b]<-P5[b,a]<-r}
for(g in c("A","V","H")){
  P5[g,"SE"]<-P5["SE",g]<-.30
  P5[g,"FF"]<-P5["FF",g]<-.18
  P5[g,"M"]<-P5["M",g]<-.24
  P5[g,"C"]<-P5["C",g]<-.20
}

P7base <- matrix(c(
1,.30,.35,.28,.12,.22,.18,
.30,1,.25,.15,.30,.12,.25,
.35,.25,1,.25,.10,.20,.16,
.28,.15,.25,1,.10,.32,.20,
.12,.30,.10,.10,1,.08,.28,
.22,.12,.20,.32,.08,1,.16,
.18,.25,.16,.20,.28,.16,1),7,7,byrow=TRUE)
P7 <- .75*P3 + .25*P7base
colnames(P7)<-rownames(P7)<-facs
truth_phi <- list(M3=P3,M4=P4,M5=P5,M7=P7)

native <- paste(
  'A =~',paste(paste0('A',1:5),collapse='+'),
  '\nV =~',paste(paste0('V',1:5),collapse='+'),
  '\nH =~',paste(paste0('H',1:5),collapse='+'),
  '\nSE =~',paste(paste0('SE',1:6),collapse='+'),
  '\nFF =~',paste(paste0('FF',1:5),collapse='+'),
  '\nM =~',paste(paste0('M',1:4),collapse='+'),
  '\nC =~',paste(paste0('C',1:8),collapse='+'))
mods <- list(
  M3=paste(native,'\nTUD =~ A + V + H\nEMO =~ SE + FF\nBODY =~ M + C\nTUD ~~ EMO + BODY\nEMO ~~ BODY'),
  M4=paste(native,'\nTUD =~ A + V + H\nBODY =~ M + C\nTUD ~~ SE + FF + BODY\nSE ~~ FF + BODY\nFF ~~ BODY'),
  M5=paste(native,'\nTUD =~ A + V + H\nTUD ~~ SE + FF + M + C\nSE ~~ FF + M + C\nFF ~~ M + C\nM ~~ C'),
  M7=native
)

simdat <- function(N,Phi,seed){
  set.seed(seed)
  F <- rmvt(N,sigma=Phi,df=8,type="shifted")
  F <- scale(F)
  X <- matrix(NA_integer_,N,length(items))
  for(j in seq_along(items)){
    k <- match(groups[j],facs)
    y <- loads[j]*F[,k] + sqrt(1-loads[j]^2)*rnorm(N)
    X[,j] <- findInterval(y,thr[[as.character(cats[j])]])+1L
  }
  d <- as.data.frame(X)
  names(d)<-items
  for(nm in names(d)) d[[nm]] <- ordered(d[[nm]])
  d
}

fit_from_stats <- function(model,ss,W,G,TH,N){
  thidx <- rep(seq_along(items),times=cats-1L)
  names(thidx)<-names(TH)
  attr(TH,"th.idx")<-thidx
  colnames(ss$cov)<-rownames(ss$cov)<-items
  MEAN<-setNames(rep(0,length(items)),items)
  fit <- cfa(
    model,
    sample.cov=ss$cov,
    sample.mean=MEAN,
    sample.th=TH,
    sample.nobs=N,
    ordered=items,
    estimator="WLSMV",
    std.lv=TRUE,
    parameterization="theta",
    wls.v=W,
    nacov=G
  )
  fm<-fitMeasures(fit,c("cfi.scaled","tli.scaled","rmsea.scaled","srmr"))
  list(fit=fit, fm=fm)
}

one_rep <- function(repi){
  seed <- 910000000L + N*10000L + match(TRUTH,c("M3","M4","M5","M7"))*1000000L + SHARD*1000L + repi
  t0 <- proc.time()[3]
  tryCatch({
    d <- simdat(N,truth_phi[[TRUTH]],seed)
    h1 <- lavCor(d,ordered=items,se="standard",test="standard",output="lavaan")
    ss<-lavInspect(h1,"sampstat"); W<-lavInspect(h1,"wls.v"); G<-lavInspect(h1,"gamma"); TH<-lavInspect(h1,"th")
    need <- if(TRUTH=="M3") c("M3","M4","M5","M7") else c("M3",TRUTH)
    fits <- lapply(need,function(m) fit_from_stats(mods[[m]],ss,W,G,TH,N))
    names(fits)<-need
    m3 <- fits[["M3"]]$fm
    absok <- m3["cfi.scaled"]>=.95 && m3["tli.scaled"]>=.95 &&
             m3["rmsea.scaled"]<=.06 && m3["srmr"]<=.08
    worse <- FALSE
    lrt_any <- FALSE
    lrt_all_available <- TRUE
    for(m in setdiff(need,"M3")){
      z <- fits[[m]]$fm
      practical <- ((m3["cfi.scaled"]-z["cfi.scaled"]) < -.010) ||
                   ((m3["rmsea.scaled"]-z["rmsea.scaled"]) > .015) ||
                   ((m3["srmr"]-z["srmr"]) > .010)
      lrt <- try(lavTestLRT(fits[["M3"]]$fit,fits[[m]]$fit,method="satorra.2000"),silent=TRUE)
      if(inherits(lrt,"try-error")){
        lrt_all_available <- FALSE
        sig <- FALSE
      } else {
        pcol <- grep("Pr\\(>Chisq\\)",colnames(lrt),value=TRUE)
        sig <- length(pcol)>0 && is.finite(lrt[2,pcol]) && lrt[2,pcol] < .05
      }
      lrt_any <- lrt_any || sig
      worse <- worse || (practical && sig)
    }
    support <- absok && !worse
    data.frame(
      N=N,truth=TRUTH,shard=SHARD,rep=repi,seed=seed,status="OK",
      m3_support=as.integer(support),
      m3_cfi=unname(m3["cfi.scaled"]),m3_tli=unname(m3["tli.scaled"]),
      m3_rmsea=unname(m3["rmsea.scaled"]),m3_srmr=unname(m3["srmr"]),
      lrt_all_available=as.integer(lrt_all_available),
      elapsed=proc.time()[3]-t0
    )
  }, error=function(e){
    data.frame(N=N,truth=TRUTH,shard=SHARD,rep=repi,seed=seed,status=paste0("ERROR:",conditionMessage(e)),
      m3_support=NA,m3_cfi=NA,m3_tli=NA,m3_rmsea=NA,m3_srmr=NA,lrt_all_available=0,elapsed=proc.time()[3]-t0)
  })
}

cores <- max(1L,min(4L,detectCores()))
res <- mclapply(seq_len(REPS),one_rep,mc.cores=cores)
out <- do.call(rbind,res)
write.csv(out,OUT,row.names=FALSE)
cat("ROWS=",nrow(out)," OK=",sum(out$status=="OK")," ERR=",sum(out$status!="OK"),"\n",sep="")
cat("SUPPORT_RATE=",mean(out$m3_support,na.rm=TRUE),"\n",sep="")
cat("LRT_AVAILABLE_RATE=",mean(out$lrt_all_available,na.rm=TRUE),"\n",sep="")
cat("MEAN_ELAPSED=",mean(out$elapsed,na.rm=TRUE),"\n",sep="")
