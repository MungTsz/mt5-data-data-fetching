# Data Fetching Changelog

## [Unreleased]

## [0.2.0] - 2024-01-02

### Added

- **Error Message in Main Function:** Introduction of error messages within the main function to enhance debugging.

- **Config Timeframe Functionality:** Enhanced the 'config timeframe' feature to support a list of specific timeframes or an "all" option, which outputs a complete timeframe list in the script.

- **Config Pair Functionality:** Updated the 'config pair' feature to allow a list of specific pairs or an "all" option, which then outputs a complete pair list in the script.

### Changed

- **MT5 Now Datetime Timezone Handling:** Modified the 'mt5_now_datetime' to first obtain the current Israel datetime, convert it to a string (eliminating the UTC time offset), and then reconvert it back to a datetime object localized with the UTC timezone. This ensures compatibility with the MT5 'copy_rates_from' function, which requires UTC timezoned datetimes.
- **If-Else Logic:** Refined the if-else logic structures for enhanced performance and readability.
- **Argument Types:** Specification of argument types to improve code clarity and function predictability.

## [0.3.0] - 2024-01-17

### Added

- **Enhancing S3 File Upload with Partition Feature:** Implementing partition feature for S3 path during local to S3 file upload

### Changed

- **Enhancing Dictionary Value Recognition with Clear Naming:** To improve the recognition of timeframe dictionary values, it is necessary to rename mt5_timeframe with clearer indications(i.e. timeframe_value).

### Fixed

- **Datetime Configuration Problem:** Fix the output in configuring datetime when the input type equals to range.
