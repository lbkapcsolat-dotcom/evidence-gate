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
                    "M5_FAIL", "M7_FAIL", "M4_INVALID_FIT", "REPLICATION_FAIL")
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

cat("PASS_ROW_SCHEMA_ALL_STATES_AND_CSV_TYPES\n")
