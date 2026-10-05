# The design rule now in force

**Python adds only what JSON cannot express itself.** Everything else is a plain
dict handed to JBrowse.

The public surface is six names, and each earns its place by that bar:

|                                  | why it survives             |
| -------------------------------- | --------------------------- |
| `LinearGenomeView`, `JBrowseApp` | the widgets                 |
| `features_track`                 | a DataFrame is not JSON     |
| `add_local_file`                 | bytes are not JSON          |
| `fetch_hub`, `plugin`            | a network fetch is not JSON |

A **trait** is not a helper and does not count against that bar —
`configuration` is JBrowse's root config block handed straight over, so `theme`,
`preferences`, `rpc` and `formatDetails` all arrived without a Python name each.
Adding a trait that passes a config dict through is the shape to reach for;
adding a function that _shapes_ one is not.

`track`, `view`, `linear_view`, `synteny_view`, `dotplot_view`, `synteny_track`,
`make_assembly` and `protein_view` were all deleted: each returned a dict
literal, and each had to grow whenever JBrowse gained a type. If you are about
to add a helper that shapes config, don't — put the dict in the docs instead.
The payoff is that a view type, adapter or display JBrowse adds needs
**nothing** here.
