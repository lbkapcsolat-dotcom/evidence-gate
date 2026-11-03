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

# Reject malformed worker outputs before rbind can coerce or silently corrupt rows.
bind_result_rows <- function(rows) {
  exemplar <- canonical_result_row(0L, "", 0L, 0L, 0L, "ERROR")
  expected_names <- names(exemplar)
  expected_types <- vapply(exemplar, typeof, character(1))
  if (!is.list(rows) || length(rows) == 0L)
    stop("HOLD_EMPTY_RESULT_ROWS")
  for (i in seq_along(rows)) {
    row <- rows[[i]]
    if (!is.data.frame(row) || nrow(row) != 1L ||
        !identical(names(row), expected_names) ||
        !identical(vapply(row, typeof, character(1)), expected_types))
      stop(sprintf("HOLD_RESULT_ROW_CONTRACT_AT_%d", i))
  }
  do.call(rbind, rows)
}

# A CSV is text: force the declared types when reloading any source or repaired shard.
read_canonical_grid_csv <- function(path) {
  classes <- c(N="integer", truth="character", shard="integer", rep="integer",
               seed="integer", status="character", m3_support="numeric",
               m3_cfi="numeric", m3_tli="numeric", m3_rmsea="numeric",
               m3_srmr="numeric", elapsed="numeric", lavaan="character")
  x <- read.csv(path, stringsAsFactors=FALSE, colClasses=classes)
  if (length(names(x)) != length(classes) ||
      !setequal(names(x), names(classes)))
    stop("HOLD_GRID_CSV_COLUMNS")
  x <- x[, names(classes), drop=FALSE]
  expected_types <- c(vapply(canonical_result_row(0L, "", 0L, 0L, 0L, "ERROR"),
                              typeof, character(1)), lavaan="character")
  if (!identical(vapply(x, typeof, character(1)), expected_types))
    stop("HOLD_GRID_CSV_TYPES")
  x
}
