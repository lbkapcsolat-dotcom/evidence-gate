source("research/eq3d_wlsmv_1000rep_v1/row_contract.R")

expected <- c("N", "truth", "shard", "rep", "seed", "status",
              "m3_support", "m3_cfi", "m3_tli", "m3_rmsea", "m3_srmr", "elapsed")
expected_types <- c(N="integer", truth="character", shard="integer", rep="integer",
                    seed="integer", status="character", m3_support="double",
                    m3_cfi="double", m3_tli="double", m3_rmsea="double",
                    m3_srmr="double", elapsed="double")

ok <- canonical_result_row(4800L, "M4", 1L, 1L, 123L, "OK",
                           1L, .99, .99, .01, .01, 2.0)
failure_states <- c("SIM_FAIL", "LAVCOR_FAIL", "M3_FAIL", "M4_FAIL",
                    "M5_FAIL", "M7_FAIL", "M3_INVALID_FIT", "M4_INVALID_FIT",
                    "M5_INVALID_FIT", "M7_INVALID_FIT", "REPLICATION_FAIL")
errors <- lapply(seq_along(failure_states), function(i) {
  canonical_result_row(4800L, "M4", 1L, as.integer(i + 1L),
                       as.integer(123L + i), failure_states[[i]], elapsed=1.0)
})
rows <- c(list(ok), errors)
for (row in rows) {
  stopifnot(is.data.frame(row), nrow(row) == 1L, ncol(row) == 12L)
  stopifnot(identical(names(row), expected))
  stopifnot(identical(vapply(row, typeof, character(1)), expected_types))
}
mixed <- bind_result_rows(rows)
stopifnot(is.data.frame(mixed), nrow(mixed) == length(rows), ncol(mixed) == 12L)
stopifnot(identical(names(mixed), expected))
stopifnot(identical(vapply(mixed, typeof, character(1)), expected_types))
stopifnot(identical(mixed$rep, seq_along(rows)))
stopifnot(identical(mixed$status, c("OK", failure_states)))
stopifnot(all(is.na(mixed$m3_support[-1L])), all(is.na(mixed$m3_cfi[-1L])),
          all(is.na(mixed$m3_tli[-1L])), all(is.na(mixed$m3_rmsea[-1L])),
          all(is.na(mixed$m3_srmr[-1L])))

bad_width <- ok[, -12L, drop=FALSE]
bad_order <- ok[, rev(expected), drop=FALSE]
bad_type <- ok
bad_type$m3_support <- 1L
bad_worker <- structure("worker crashed", class="try-error")
for (bad in list(bad_width, bad_order, bad_type, bad_worker)) {
  result <- try(bind_result_rows(list(ok, bad)), silent=TRUE)
  stopifnot(inherits(result, "try-error"))
}

# Source-run artifacts predate row_contract.R and serialize a different order.
legacy_order <- c("rep", "seed", "status", "m3_support", "m3_cfi", "m3_tli",
                  "m3_rmsea", "m3_srmr", "elapsed", "N", "truth", "shard", "lavaan")

# CSV round-trip must preserve all 13 on-disk columns and their types.
output <- mixed
output$lavaan <- "0.7.2"
f <- tempfile(fileext=".csv")
write.csv(output, f, row.names=FALSE)
reloaded <- read_canonical_grid_csv(f)
unlink(f)
stopifnot(identical(names(reloaded), c(expected, "lavaan")))
stopifnot(identical(vapply(reloaded, typeof, character(1)),
                    c(expected_types, lavaan="character")))
stopifnot(identical(reloaded$status, mixed$status))
legacy_file <- tempfile(fileext=".csv")
write.csv(output[, legacy_order, drop=FALSE], legacy_file, row.names=FALSE)
legacy_reloaded <- read_canonical_grid_csv(legacy_file)
unlink(legacy_file)
stopifnot(identical(names(legacy_reloaded), c(expected, "lavaan")))
stopifnot(identical(vapply(legacy_reloaded, typeof, character(1)),
                    c(expected_types, lavaan="character")))
stopifnot(identical(legacy_reloaded$rep, mixed$rep))



# P0 evidence: the aggregator must reject duplicate / mislabeled / missing shards.
test_shard <- do.call(rbind, lapply(seq_len(250L), function(i) {
  canonical_result_row(4800L, "M4", 0L, i, as.integer(5000L + i),
                       "OK", 1L, .99, .99, .01, .01, .5)
}))
test_shard$lavaan <- "0.7.2"
stopifnot(isTRUE(validate_grid_shard(test_shard, 4800L, "M4", 0L)))
negative_shards <- list(
  test_shard[-250L, , drop=FALSE],
  within(test_shard, rep[250L] <- 249L),
  within(test_shard, N[1L] <- 6000L),
  within(test_shard, truth[1L] <- "M3"),
  within(test_shard, shard[1L] <- 1L),
  within(test_shard, lavaan[1L] <- "UNKNOWN")
)
for (broken in negative_shards)
  stopifnot(inherits(try(validate_grid_shard(broken, 4800L, "M4", 0L),
                         silent=TRUE), "try-error"))

all_names <- unlist(lapply(c(4800L,6000L,7200L), function(n)
  unlist(lapply(c("M3","M4","M5","M7"), function(m)
    paste0("grid-N",n,"-",m,"-s",0:3)))))
paths <- file.path("artifacts", all_names, "grid.csv")
stopifnot(isTRUE(validate_grid_artifact_inventory(paths)))
bad_paths <- paths
bad_paths[48L] <- bad_paths[1L]
stopifnot(inherits(try(validate_grid_artifact_inventory(bad_paths),
                       silent=TRUE), "try-error"))

cat("PASS_ROW_SCHEMA_ALL_STATES_AND_CSV_TYPES\n")
