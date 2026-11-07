# Store writes with a second writer

Plan 3 Task 6b adds the in-process reminder ticker as a second writer, alongside Telegram
button presses and agent tools (and the `stash tick` cron fallback, which runs in its own
process). This page describes the store calls that keep those writers from losing each
other's changes. The source of truth for behaviour is still the spec and the Plan 3 text.

## Changing an existing item: `update_item`

```python
from stash.store import StaleItemError, UnknownItemError

read = store.get_item("i1")
store.update_item(read.kept_as(True, now), replacing=read)
```

1. It replaces the stored item when the item exists and still equals `replacing`, the item
   as it was read. It never creates an item.
2. An item deleted after it was read raises `UnknownItemError(item_id)` and stays deleted.
3. An item that another writer changed after it was read raises `StaleItemError(item_id)`,
   and the other writer's change is kept. Any field counts, not only `updated_at`, so two
   writes in the same clock tick are still told apart.
4. A missing capture or parent is refused the same way `save_item` refuses it:
   `UnknownCaptureError` or `UnknownItemError(parent_id)`.

`record_completion(item, outcome, *, replacing=read)` follows the same rules. `save_item`
(create or replace) is only for filing new items (`stash.capture.pipeline`), and an
architecture test keeps it there.

## Grouping: `group_item`

```python
child, parent = store.get_item("ramen"), store.get_item("japan-trip")
store.group_item(child.grouped_under(parent, now), replacing=child)
```

5. The checks and the write happen in one transaction. On top of the `update_item` rules:
   - a missing parent raises `UnknownItemError(parent_id)`;
   - a parent that is itself in a group raises `ParentIsGroupedError(parent_id)`;
   - a child that holds items raises `ChildHoldsItemsError(child_id)`.

   `Item.grouped_under` still refuses a parent that was grouped when it was read. The store
   check is the backstop for a race.

## What the owner sees

6. `Lifecycle` (complete, keep, reopen, drop, didn't happen, set stage, group, ungroup)
   answers an item deleted meanwhile with `UnknownItem`, the same answer as for an unknown
   id. The Telegram reply is "That item no longer exists."
7. An item changed meanwhile gets `ItemChanged`. On a Telegram button, including the Type
   and Stage fixes, the reply is "That changed meanwhile — try again." An agent tool returns
   the error text.
8. A store that stays busy (see below) gets `StashBusy`. The button reply is "The stash is
   busy — try again in a moment."
9. Grouping refusals keep their existing wording.

## Recording a sent message: `record_all_sent`

```python
recorded_all = store.record_all_sent(message.nudges, sent_at)
```

10. All of a message's ledger rows are written in one transaction. If the process fails
    part-way, none are recorded and the whole message is due again. It is never
    half-recorded.
11. It returns `False` when another sender had already recorded one of the rows (a lost
    race). The other rows are still recorded, because this message was sent, so they are not
    sent again. `Nudger.mark_sent` returns this value.

## Waiting for the write lock

12. A transaction (`record_completion`, `update_item`, `group_item`, `save_steps`,
    `save_step`, `record_all_sent`) waits up to `BUSY_TIMEOUT` (5 s) for another
    connection's write lock. After that it raises `StoreBusyError` and releases the store for
    the next call.
13. While it waits, it holds the store's in-process lock. This is intended: the store shares
    one SQLite connection across threads, and a transaction on that connection must not
    interleave with another thread's statements.
14. When a transaction fails, the caller gets the error that caused the failure, whether it
    came from a statement or from `COMMIT`. A follow-on "no transaction is active" rollback
    error never replaces it.
