# Changelog

## 2026-02-13
- Added form type mapping for `consultation` and kept `tag`/`tender.status` handling in `bt_03`.
- Added `tedNoticeType` at root from `cbc:NoticeTypeCode` in `bt_03`.
- Added `tender.internalId` from `ProcurementProject/ID[@schemeName='InternalID']` in `bt_22_procedure`.
- Moved tender result flags into awards and renamed fields:
  - `TenderResultCode` -> `awards[].tedStatus`
  - `DecisionReasonCode` -> `awards[].tedStatusDecision`
- Added `duration` and `durationUnit` alongside `durationInDays` in BT-36 (lot/part) and BT-98 (lot).
- Added `euFunded` boolean per lot based on `FundingProgramCode[@listName='eu-funded']` in `bt_60_lot`.
- Built coherent award criteria objects from `SubordinateAwardingCriterion` and flattened numeric fields (no `numbers[]`) in `bt_award_criteria_subordinate`.
- Reworked procedure delivery addresses: build one address per `RealizedLocation` and replaced the procedure-level BT-5071/5101/5121/5131/5141/728 handlers.
- Reworked lot delivery addresses under `tender.items` similarly (one address per `RealizedLocation`) and replaced lot-level BT-5071/5101/5121/5131/5141/728 handlers.
