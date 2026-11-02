canonical_result_row <- function(N, truth, shard, rep, seed, status,
                                 m3_support=NA, m3_cfi=NA, m3_tli=NA,
                                 m3_rmsea=NA, m3_srmr=NA, elapsed=NA) {
  data.frame(
    N=as.integer(N),
    truth=as.character(truth),
    shard=as.integer(shard),
    rep=as.integer(rep),
    seed=as.integer(seed),
    status=as.character(status),
    m3_support=as.numeric(m3_support),
    m3_cfi=as.numeric(m3_cfi),
    m3_tli=as.numeric(m3_tli),
    m3_rmsea=as.numeric(m3_rmsea),
    m3_srmr=as.numeric(m3_srmr),
    elapsed=as.numeric(elapsed),
    stringsAsFactors=FALSE
  )
}
