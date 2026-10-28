"""English narrative for the final, implemented HealthRetailers warehouse."""
PAGES=[]
def page(title,*blocks):PAGES.append((title,list(blocks)))
def p(text):return ('p',text)
def h(text):return ('h',text)
def fig(name,caption,width=6.85,maxheight=4.8):return ('fig',name,caption,width,maxheight)
def table(headers,rows,widths=None):return ('table',headers,rows,widths)
def code(text):return ('code',text)

page('1 Project purpose and final scope',
 p('HealthRetailers is a retail data warehouse project. A data warehouse is a database organized for analysis across business activities and time. The final implementation imports dirty production exports, preserves their values in staging, derives consistent business descriptions and loads a warehouse with five dimensions and two fact tables.'),
 p('A dimension describes an analysis subject, such as a product or supplier. A fact table records measurements at a precisely defined level of detail. Here, stock records current quantities by product, while purchases record quantities and net amounts by validated supplier invoice line.'),
 fig('journey','The complete implemented journey. The 244300 rows belong to the 17 sources used by this version, not to every file in the wider original repository.',maxheight=1.55),
 h('How the project reached this version'),
 p('The original DataWarehouseProject_3AI4 repository was cloned with its remote branches available. Its wider dirty-data collection contains 29 source exports. An earlier, broader warehouse implementation remains in that separate repository. It is not called by the final Master package described here.'),
 p('The working base then switched to Amal’s HealthRetailers_DW repository. Her two-package staging and dimension structure, four dimension diagrams, Sort and Merge Join patterns, and Lookup patterns were retained. Local corrections addressed configuration, text handling, product matching and NULL comparisons. Two fact Data Flows were then added inside her ETL_SA_DW package.'),
 p('The final deliverable is the local HealthRetailers_DW_amal project on branch codex/fix-five-dimensions. No claim is made that Amal’s remote GitHub repository was updated. Customer sales, receipts, supplier payments, machine learning and additional facts are outside this final two-fact scope.'))

page('2 Source files and data coverage',
 p('The sources are CSV exports from the production application. CSV means comma-separated values, but these files use either commas or semicolons according to their connection definition. The solution reads files; it does not connect directly to a live production database or call a production API.'),
 ('sources',),
 p('The manifest records the source filename, delimiter, decoding used, target staging table, ordered columns, row count and hashes. Appendix B lists the fields retained from each source. Rows are not globally deduplicated or deleted during transport.'),
 p('Source row counts are not expected to equal dimension counts. For example, 93 customer-export rows help identify 82 customer dimension members through company identifiers and business rules. Members include explicit unknown and anonymous entries. A dimension is a conformed description at its own grain, not a copy of one CSV.'))

page('3 What dirty data means in this project',
 p('Dirty data is information that needs interpretation, normalization or quality checks before it can support reliable analysis. Dirty does not mean every row is invalid. The aim is to preserve evidence, apply explainable rules and expose what cannot be recovered.'),
 table(['Observed issue','Why it matters','Treatment'],[
 ('Mixed UTF8 and CP1252 files','The same bytes can display different characters under the wrong encoding.','Decode the original correctly and create Unicode transport.'),
 ('Quotation and JSON text','Incorrect quote settings retain extra quotation marks or split a cell.','Parse and write CSV with consistent quoting; enable the SSIS text qualifier.'),
 ('Amounts and dates stored as text','Text cannot safely be summed or compared as a date.','Use explicit numeric conversion and month day year date parsing.'),
 ('Missing names or links','An invoice or product can lack a reliable description.','Use documented fallbacks or an explicit unknown member.'),
 ('HTML in descriptions','Markup is not the intended product label.','Strip tags and decode selected HTML entities for product matching.'),
 ('Repeated or damaged product codes','Different catalogue records can share an unreliable code.','Retain distinct attribute variants and require stronger matching for ambiguity.'),
 ('Drafts and comment lines','They are source records but not completed purchases.','Keep raw rows; route excluded purchase candidates to Rejets_Faits.'),
 ('NULL values','A normal comparison can return unknown instead of true or false.','Use explicit NULL-safe change detection.'),
 ],[1.25,2.45,3.15]),
 p('Mojibake is the damaged text produced by reading bytes with the wrong character encoding. A replacement character, written as U+FFFD, means an earlier conversion could not represent the original character. Known mojibake sequences can be repaired; an unknown original letter cannot be recovered with certainty just by guessing.'),
 p('Examples in this guide using Product A or Supplier X are fictional teaching examples. The operational totals and row counts are measured results from the implementation.'))

page('4 Architecture and the role of each tool',
 fig('architecture','The physical layers. The staging database contains the raw source tables and technical preparation objects. Both databases run on the local SQL Server instance.',maxheight=3.25),
 p('SQL Server 2022 Developer is the database engine: it stores tables, executes SQL, enforces keys and supplies data to SSIS. SA_Health_Dimensions is the staging database. DW_Health_Dimensions is the analysis database; its historical name still contains Dimensions although it now holds two facts as well.'),
 p('SSMS, SQL Server Management Studio, is a client for administering SQL Server and running queries. It is not the database itself and it does not need to stay open while packages execute.'),
 p('Visual Studio 2022 with the SSIS Projects extension opens the solution and its visual package designers. SSIS, SQL Server Integration Services, is the integration runtime that executes package tasks and Data Flows. The full SSIS 2022 runtime was added after the original environment was found to lack that feature.'),
 p('PowerShell, Python and the SSIS authoring API were used to configure and generate compatible files without operating the user’s screen. The saved package components are native SSIS components, not a custom executable pretending to be a Data Flow. DTExec executes the compiled project outside the designer.'))

page('5 One time setup and repeated execution',
 fig('setup_execution','Database creation is a setup operation. Data loading is a repeatable package execution. SQL may participate in both, but SSMS is not a required manual step for each load.',maxheight=2.65),
 p('The one-time setup creates the two databases, the five dimension tables, the two fact tables, staging tables, functions, views and procedures. It also configures local connection strings and builds the SSIS project. This setup has already been completed on the current machine.'),
 p('The scripts can be executed in SSMS with SQLCMD Mode enabled, but the supplied setup.ps1 runs them through sqlcmd. SQLCMD variables substitute the chosen database names into scripts before SQL execution. A script is a saved set of commands; a stored procedure is a named routine installed inside a database.'),
 table(['Step','What performs it','When'],[
 ('Create database objects','SQL scripts called by setup.ps1','Initial setup or an intentional schema deployment'),
 ('Prepare transport and connections','configure.py','Setup or a deliberate source/configuration refresh'),
 ('Load raw sources','EL_SI_SA.dtsx','Every Master execution'),
 ('Load calendar and dimensions','Master SQL task and ETL_SA_DW','Every Master execution'),
 ('Prepare and load the facts','Preparation task and two native Data Flows','Every Master execution'),
 ('Validate the warehouse','Master Verification SQL task','After successful loading'),
 ],[1.7,2.8,2.35]),
 p('After setup, run Master.dtsx. There is no requirement to manually execute calendar SQL or insert warehouse rows in SSMS before each run. Reading and analysing the resulting tables in SSMS is a separate activity.'))

page('6 Preserve the originals and prepare transport',
 p('The data/original folder holds the 17 selected source files byte for byte. configure.py reads each file, attempts UTF8 with optional BOM first, then falls back to CP1252 and CP850 if decoding requires it. In the measured manifest, 14 files decoded as UTF8 and three as CP1252. This is an implementation-specific decoding strategy, not a universal encoding detector.'),
 fig('transport','Transport conversion changes representation, not the parsed business values. Hashes provide separate evidence for original file bytes and loaded cell contents.',maxheight=3.25),
 p('The script parses records with the configured separator and checks the number of fields. If that separator does not match the header width, it tries the other supported separator. A remaining column mismatch fails configuration rather than padding away unexplained data.'),
 p('Parsed records are written to data/transport as UTF16 CSV with consistent CRLF record separators and quotation handling. Embedded quotation marks are escaped by the CSV writer. The SSIS flat-file managers use Unicode and a double-quote text qualifier. Every flat-file column is text-qualified.'),
 p('Unicode is a character representation that supports accented letters and many writing systems. UTF8 and UTF16 are encodings of Unicode. Changing to UTF16 does not repair already damaged source letters; it prevents a new encoding mismatch during this import. The raw files remain available for investigation.'))

page('7 Raw loading into the Staging Area',
 fig('staging','One representative raw loading path. EL_SI_SA contains 17 corresponding Flat File Source to OLE DB Destination Data Flows after its staging reset.',maxheight=1.65),
 p('Staging Area, abbreviated SA, means the intermediate database used to receive source data before warehouse loading. The raw staging tables use NVARCHAR(4000) for text fields, with NVARCHAR(MAX) for the long UsersSettings Value field. NVARCHAR stores Unicode text; MAX allows the larger text content needed here.'),
 p('Keeping numeric-looking values as text at this stage is deliberate. An amount with a comma, a blank supplier identifier or an unusual code is preserved before interpretation. Raw staging is not the final typed warehouse and is not globally cleaned in place.'),
 p('EL_SI_SA first clears the raw staging tables, then imports the configured transport files. This is a full refresh of the source staging snapshot. It does not mean that every warehouse table is truncated. Warehouse dimensions and facts use the insertion and update paths described later.'),
 table(['Input','Operation','Output'],[
 ('Transport CSV','Flat File Source reads delimited, quoted Unicode values.','An SSIS row with string columns'),
 ('SSIS row','OLE DB Destination maps the source columns to SQL columns.','A row in the corresponding *_SA table'),
 ('All source rows','Count and cell-hash checks compare the source and SQL contents.','Evidence of faithful transfer, including duplicates'),
 ],[1.4,3.7,1.75]),
 p('The 244300 loaded source records include data used for customer and payment dimensions as well as purchases and stock. Only a subset is eligible for the purchase fact. A source record may be preserved in staging without becoming a fact.'))

page('8 Master package orchestration',
 fig('master','Actual Master task order. Each connector is a success dependency: the next task runs only after its predecessor succeeds.',maxheight=1.65),
 p('A package is a saved SSIS workflow in a .dtsx file. A Control Flow describes which tasks execute and in what order. A precedence constraint is the connector that controls execution according to a condition, here success. A Data Flow describes how rows move through sources, transformations and destinations inside a task.'),
 h('What each Master task does'),
 p('EL_SI_SA is an Execute Package task that runs the raw import package. Calendrier is an Execute SQL task that fills missing dates in dim_temps. ETL_SA_DW is another Execute Package task that runs the dimension and fact Data Flows. Verification is an Execute SQL task containing the warehouse assertions.'),
 p('Amal’s original Master called staging and dimensions in sequence. Calendar loading and final verification were added so that the final entry point runs the entire implemented workflow without requiring a separate manual calendar step.'),
 p('A check that throws a SQL error causes the validation task and package execution to fail. A green task means that task completed successfully; it does not mean every source description was recoverable or every future scenario has been tested.'),
 p('To see row transformations, open EL_SI_SA or ETL_SA_DW and double-click a Data Flow task. Master is the coordinator, which is why its diagram is intentionally much simpler than the dimension or purchase diagrams.'))

page('9 Inside the warehouse loading package',
 fig('etl_control','The implemented Control Flow inside ETL_SA_DW. Four original dimension tasks precede preparation, current stock and purchases.',maxheight=4.65),
 p('The four dimension tasks have independent inputs at the Control Flow level, but this package sets MaxConcurrentExecutables to 1. Therefore they execute one at a time; the diagram is not a promise of parallel execution. All four must finish before fact preparation can begin.'),
 p('The package contains six native Data Flows: alim_dim_client, alim_dim_fournisseur, alim_dim_paiement, alim_dim_produit, alim_fait_stock_actuel and alim_fait_achats. dim_temps is the fifth dimension, but it is generated by the Master SQL task rather than a CSV Data Flow.'),
 p('Preparation des deux faits rebuilds technical caches, checks mandatory source values, clears the exclusion log and removes fact keys that are no longer eligible. The stock Data Flow then completes before the purchases Data Flow runs. SQL preparation does not replace their native warehouse INSERT and UPDATE paths.'))

page('10 The final warehouse model',
 fig('schema','The implemented seven-table model. Lines represent foreign-key relationships. Product and date are shared dimensions. Client and payment are available dimensions without a foreign-key link from these two facts.',maxheight=5.65),
 p('A star schema places a fact table at the centre of its descriptive dimensions. Because these two facts share product and date dimensions, the overall design can also be described as a small fact constellation. Shared dimensions allow consistent product and period analysis across business processes.'),
 p('Stock has one current row per product, not a history of daily captures. Its DateKey is nullable because the export does not prove a capture date. Purchases has one row per validated supplier invoice line. A repeated product on the same invoice remains several fact rows if the source contains several line identifiers.'))

page('11 Grain keys and measurable quantities',
 p('Grain is the exact meaning of one row. It must be defined before choosing the key or adding measurements. Changing grain without changing the key can duplicate amounts or overwrite valid records.'),
 table(['Table','Grain','Key'],[
 ('dim_produit','One product identifier','Product_Id'),('dim_client','One customer/company member','Company_Id'),
 ('dim_fournisseur','One supplier member','Fournisseur_Id'),('dim_paiement','One payment mode','PaymentMode_Id'),
 ('dim_temps','One calendar date','DateKey'),('fait_stock_actuel','One product in the current source snapshot','Product_Id'),
 ('fait_achats','One eligible source invoice line','Id from DocumentItem'),
 ],[1.65,3.4,1.8]),
 p('A primary key, PK, uniquely identifies a row and cannot be NULL. A foreign key, FK, requires a referenced dimension member to exist, unless that FK column permits NULL. This model keeps existing business identifiers as dimension keys; it does not introduce separate surrogate identifiers.'),
 p('A measure is a quantitative or calculated value used in analysis. Purchased quantity and net purchase amount are measures. Product family and supplier name are analysis attributes. An invoice identifier is a reference, not a value to sum.'),
 p('Additivity describes which sums make business sense. Purchase amounts can be summed across eligible lines. Quantities should be grouped by compatible products or units. Current stock quantities must not be summed across repeated snapshots. Alert thresholds and unit prices are not additive measures.'),
 p('NULL means missing or not known, not zero and not an empty string. A missing stock threshold must not automatically become zero. The supplier key -1 is a real unknown-member row, whereas a NULL stock DateKey means there is no proven calendar reference.'))

page('12 Product dimension Data Flow',
 fig('alim_dim_produit','Actual component topology reconstructed from alim_dim_produit. Original French component names are retained; this is a documentation diagram, not a screenshot.',maxheight=4.65),
 p('The source SA_Produits executes usp_source_dim_produit and declares the result columns explicitly: Product_Id, Libelle, Famille and Marque. DIM_Produit supplies existing warehouse members. Both inputs are sorted by the joining product identifier before the Merge Join.'),
 p('Sort, called Trier in the designer, orders rows by the merge key. Merge Join, called Jointure de fusion, combines the sorted source and warehouse rows. The Conditional Split then selects new products for insertion and changed products for an OLE DB Command update. Equal members need no write.'),
 p('The resulting dimension contains 6842 product members. Libelle is the descriptive name; Famille is the family; Marque is the brand. Their values can come from several sources, which is why a separate matching procedure is needed before the visible comparison and loading steps.'),
 p('The physical schema permits a nullable product label, but the final quality checks require a nonempty label. If a reliable description cannot be reconstructed, the procedure returns an explicit label such as PRODUIT INCONNU followed by the product identifier.'))

page('13 How product descriptions are reconstructed',
 fig('product_matching','The source procedure builds evidence and chooses one catalogue variant. It does not globally assume that a product code is unique.',maxheight=4.6),
 p('The procedure keeps the latest product event by event identifier and extracts product id, code and label from JSON. JSON is structured text made of named values. It also links document item descriptions to products through ProductStocks, cleans HTML and builds alternative label evidence.'),
 p('Catalogue records are deduplicated by code, label, family and brand together. A technical ExportId distinguishes the retained variants. This fixes the earlier assumption that one code always represented one reliable catalogue row.'),
 p('Candidate priority is code agreement first, document-line label agreement second and event-label agreement third. An ambiguous repeated code must also agree with the event label. Candidate ordering then prefers a populated family and uses code and ExportId to choose one result.'),
 p('An exact binary test rejects catalogue labels containing the replacement character. Label fallback is then document-line description, event label, and finally an explicit unknown label. Family defaults to NON RENSEIGNE. Brand uses the catalogue, a known-brand prefix inferred from the chosen label, or NON RENSEIGNE. Missing letters are not invented.'))

page('14 Client dimension Data Flow',
 fig('alim_dim_client','The original client comparison pattern uses two sorted inputs, Merge Join, Conditional Split and separate insert and update destinations.',maxheight=4.6),
 p('Candidate identifiers come from eligible validated sales documents and their transactions, explicit special members, and company/customer-export code matches. Related-document and product-line conditions help define the source client population. These rules support the dimension even though a sales fact is outside the final scope.'),
 p('The name is taken from the repaired customer label or company name. An em dash can separate a descriptive prefix from the name. TypeClient classifies known labels as PARTICULIER, B2B - LABORATOIRE, COMPTOIR_ANONYME or NON RENSEIGNE.'),
 p('Company_Id 2 is Client comptoir (anonyme), a walk-in anonymous customer. It must not be counted as an identified person. The unknown member -1 and anonymous member 2 have EstClientIdentifie = 0; other retained identifiers have 1. The dimension has 82 members, not 82 identified people.'),
 p('The corrected comparisons update a name or classification even when the existing destination value is NULL. Changes replace existing attributes, following Slowly Changing Dimension type 1, abbreviated SCD type 1. No history row is created.'))

page('15 Supplier dimension Data Flow',
 fig('alim_dim_fournisseur','Actual supplier topology. A Lookup no-match path inserts a member; matched members go through change detection before UPDATE.',maxheight=4.3),
 p('Supplier candidates include companies marked CompanyType_Id = 2 and identifiers required by validated purchase invoices or supplier credit notes. Including credit-note suppliers in the dimension does not mean credit-note facts are loaded.'),
 p('The source combines CompaniesList and the supplier export by business code. It removes the supplier label’s numeric list prefix when applicable and repairs known accent sequences. It falls back to the company name or an explicit supplier-unknown label when necessary.'),
 p('Lookup, called Recherche in some diagrams, searches the reference table for a matching key. If the key is absent, the destination inserts it. If present, the Conditional Split compares names and routes only a change to the OLE DB Command. The NULL-safe expression prevents a missing old name from stopping the flow.'),
 p('There are 116 supplier members, including the -1 NON RENSEIGNE member. Thirteen eligible purchase lines have an unassigned source supplier and reference -1. Empty identifiers are normalized to NULL before conversion, preventing SQL from accidentally converting an empty string into key 0.'))

page('16 Payment mode dimension Data Flow',
 fig('alim_dim_paiement','The payment-mode diagram retains Amal’s Lookup, no-match INSERT and matched-row Conditional Split UPDATE pattern.',maxheight=4.3),
 p('The source reads distinct payment modes from PaymentsList_SA and translates known application labels into readable names. The resulting identifiers are 1, 5, 7, 11, 21 and -1, covering cheque, cash, bank card, deferred payment, tokens and an unknown member.'),
 p('The mode name is PaymentModeName. It describes how payment occurs. It is not a monetary measure and does not mean the invoice has already been paid. The mode named credit or deferred payment is also different from a supplier credit note, which is a document reversing part of a purchase.'),
 p('This version retains all six payment-mode dimension members but does not create a payment fact. Neither current stock nor purchase invoice lines require a payment-mode FK. Joining every payment directly to every invoice line could multiply amounts, so the purchase source deliberately avoids that join.'),
 p('As in the supplier flow, new identifiers are inserted and changed labels are updated. Existing NULL values are compared explicitly. The regression tests intentionally change a payment label and verify that the source value is restored.'))

page('17 Time dimension and the business calendar',
 p('The Master task Calendrier runs the calendar SQL directly. It inserts missing dates from 30 September 2024 through 29 September 2026 inclusive, giving 730 rows. It does not delete existing dates or reload them unnecessarily.'),
 table(['Field','Meaning','Illustration'],[
 ('DateKey','Integer date key in YYYYMMDD format','20241113'),('Date','Actual SQL date','13 November 2024'),
 ('Annee','Calendar year','2024'),('Trimestre','Calendar quarter from 1 to 4','4'),('Mois','Month from 1 to 12','11'),
 ('SemaineISO','ISO week number','Based on ISO week rules, not a simple count from 1 January'),('EstFerie','Holiday indicator','1 for the configured holiday set, otherwise 0'),
 ],[1.55,2.7,2.6]),
 p('DateKey is calculated as year times 10000 plus month times 100 plus day. Purchase DateKey uses the invoice date. The SQL source parses the original month/day/year representation explicitly with conversion style 101; it does not rely on an ambiguous machine locale.'),
 p('The inherited holiday logic uses the French holiday set: 1 January, 1 and 8 May, 14 July, 15 August, 1 and 11 November, 25 December, Easter Monday, Ascension and Whit Monday. Easter is calculated using the Gregorian algorithm. The business country must confirm this inherited choice; this is not a Tunisian holiday implementation.'),
 p('The calendar extends beyond the real purchase dates and does not generate synthetic purchase records. There is no fabricated capture date for stock. A future snapshot history would require a reliable capture date and a different product-by-date fact key.'),
 h('What the calendar check proves'),
 p('The validation checks 730 rows and verifies DateKey, year, month, quarter and ISO week against the stored SQL date. It verifies consistency with the implemented calendar rules, not the appropriateness of the holiday country for every business.'))

page('18 Shared transformation rules',
 p('fn_reparer_accents replaces a limited list of known mojibake sequences under a binary collation. fn_texte_html removes HTML tags by replacing them with spaces, decodes selected entities such as ampersands and nonbreaking spaces, and trims/collapses extra spaces. These functions are applied in the relevant source logic, not as an undocumented global rewrite of every raw column.'),
 p('Collation is the rule SQL Server uses to compare and sort text. CI_AI comparisons ignore case and accents for matching labels. Binary comparisons inspect exact character values when identifying corruption. The binary check matters because the replacement character can behave unexpectedly under a linguistic collation.'),
 table(['New value','Existing value','Changed'],[
 ('NULL','NULL','No'),('A known value','NULL','Yes'),('NULL','A known value','Yes'),('The same non-NULL value','The same value','No'),('A different non-NULL value','An old value','Yes'),
 ],[2.25,2.45,2.15]),
 p('A normal new_value != old_value expression can return NULL if either side is NULL. A Conditional Split needs a definite Boolean result. The implemented ternary expression first checks missingness, and only compares values when both are non-NULL.'),
 code('ISNULL(NewValue) ? !ISNULL(OldValue) :\n    (ISNULL(OldValue) ? TRUE : NewValue != OldValue)'),
 p('fn_nombre_fait removes ordinary and selected nonbreaking spaces, changes a decimal comma to a dot and uses TRY_CONVERT(decimal(18,4)). TRY_CONVERT returns NULL instead of raising a conversion error. The mandatory-value guards then decide whether that missing result is acceptable or must stop the load. A failed numeric conversion is not silently replaced with zero.'))

page('19 Prepare the facts before loading',
 fig('prepare_facts','usp_preparer_faits is called automatically by the preparation SQL task after the dimensions. It prepares inputs and removes ineligible keys; it does not insert the final warehouse facts.',maxheight=3.8),
 p('CatalogueSeuils_Faits caches catalogue code, repaired label and numeric threshold. CodesProduits_Faits caches the latest product-event code with Product_Id as a primary key. Indexes make these repeated lookups inexpensive. Both caches are rebuilt from current staging before the fact Data Flows run.'),
 p('Caching was introduced because repeated repairs and repeated JSON extraction inside joined queries made stock validation slow. In the recorded performance check, reading the full stock candidate aggregate after preparation took about 250 milliseconds. This is a measured local query result, not a promised runtime for the whole pipeline.'),
 p('The guards reject stock records with an invalid product key or quantity. For validated purchase lines they require valid line/document identifiers and dates. A commercial product line also requires quantity, amount and a calculable net amount. A no-product line with a nonzero amount fails instead of disappearing as a comment.'),
 p('The procedure clears Rejets_Faits, deletes stock facts whose product key is absent from current candidates, and deletes purchase facts whose line is no longer a validated commercial candidate. This deletion is necessary for source status changes; an upsert alone would leave a previously valid but now-draft invoice in the warehouse.'))

page('20 Current stock Data Flow',
 fig('alim_fait_stock_actuel','Actual alim_fait_stock_actuel topology. The diagram shows source, derived columns, product Lookup, existing-fact Lookup and separate native INSERT and UPDATE paths.',maxheight=4.9),
 p('v_source_stock groups source ProductStocks rows by typed Product_Id and sums their quantities. If a stock quantity cannot be converted, the product’s derived quantity becomes NULL and preparation fails explicitly. Negative balances are retained rather than changed to zero.'),
 p('The source retrieves alert thresholds by the latest product-event code first, then by the conformed product label as a fallback. Threshold groups return a value only when the non-NULL candidates agree. An absent or conflicting threshold remains NULL. The view uses dim_produit as a label reference after that dimension has loaded.'),
 p('The Derived Column transformation sets DateKey to NULL and calculates EstSousSeuil. Lookup dim_produit checks the product reference. Lookup of the existing fact separates a new product from a current stock row. Changed measures are updated; an identical row needs no write. A missing required dimension reference fails the flow.'))

page('21 Understand stock measures and unknown dates',
 table(['Column','Source or calculation','Business meaning'],[
 ('Product_Id','Typed ProductStocks.Product_Id','The current product key, also the fact PK'),
 ('DateKey','NULL by design','The capture date is not established by the export'),
 ('QuantiteActuelle','Sum of ProductStocks.Quantity by product','Current source balance'),
 ('QuantiteAlerte','Consistent catalogue threshold using code or label matching','Reorder comparison threshold; may be unknown'),
 ('EstSousSeuil','Quantity < threshold; NULL if threshold is NULL','1 means below threshold, 0 means not below'),
 ],[1.5,3.1,2.25]),
 h('Worked example'),
 p('Suppose Product A has a balance of 8 and an alert threshold of 10. Its alert indicator is 1 because 8 is less than 10. A balance of exactly 10 produces 0. If the threshold is missing, the indicator is NULL; it is not evidence that the product is safe or below threshold.'),
 p('The delivered snapshot has 6842 products and total source quantity 18800. There are 4449 products with known thresholds and 2195 below their known threshold. The remaining 2393 thresholds are unknown. These figures must be interpreted with product-unit compatibility in mind; the total quantity is a source reconciliation, not a universal business unit.'),
 p('The date of the last sale, last stock movement or current ETL execution does not prove the date of the exported stock snapshot. DateKey therefore remains NULL. This is an explicit limitation, not a failed date conversion.'),
 p('To keep several captures in the future, use a reliable capture date and change the grain and key to product plus capture date. The current Product_Id primary key intentionally overwrites the same product’s current balance instead of retaining daily history.'),
 p('Alert thresholds are control values, not values to sum in a dashboard. Compare each product’s balance with its own threshold. The stock flag is calculated at the product grain and can be counted to answer how many products need attention.'))

page('22 Construct purchase candidates from staging',
 fig('purchase_joins','The purchase source joins four staging subjects. Document line identifiers preserve the fact grain; payment rows are not part of this join.',maxheight=3.45),
 p('DocumentItem supplies line Id, Document_Id, ProductStock_Id, Quantity and PrixTotalHt. Documents supplies the invoice date, state, type, transaction reference and TotalNetHt. ProductStocks translates the stock identifier to Product_Id. Transactions supplies the supplier/company identifier.'),
 p('The source view filters to DocumentType_Id 20, the supplier invoice type in this data. IsValidated is true only for State 1. The view still presents draft invoice lines to the Data Flow so that the Conditional Split can document their exclusion. Supplier credit notes, type 23, are outside this fact scope.'),
 p('Before numeric conversion, empty identifier strings become NULL using NULLIF after trimming. This prevents the empty-string-to-zero conversion that originally created unmatched supplier key 0. Unassigned suppliers become the existing member -1.'),
 p('The source uses joins and window calculations to prepare net line amounts. A window function calculates values within an invoice while retaining each individual line row. It does not collapse an invoice to one fact record. All joining and allocation logic is installed in the documented SQL view, read by the native OLE DB Source.'))

page('23 Purchase selection and dimension lookups',
 fig('purchase_selection','The first part of the actual purchase Data Flow. The existing-fact upsert that follows is shown in the next figure. This split presentation keeps the full flow readable.',maxheight=5.25),
 p('The first Derived Column assigns the fact name and a selection reason. BROUILLON means draft. SANS_PRODUIT identifies no-product candidates. ACCEPTE is the accepted commercial route. The Conditional Split sends excluded rows to Rejets_Faits in staging, retaining source line Id and reason.'),
 p('Accepted rows receive DateKey, QuantiteAchetee and MontantAchat_HT through visible Derived Column expressions. Three Lookups verify date, product and supplier keys. Their required-reference behavior is fail on no match; a broken dimension reference is not silently ignored.'),
 p('The measured source contains 7027 type-20 candidate lines. Of these, 6964 commercial lines on validated invoices are loaded, 49 draft lines and 14 valid-invoice comment lines are logged as exclusions. This accounts for every candidate row in this dataset.'))

page('24 Native insertion and update decisions',
 fig('upsert','The shared existing-key pattern used by both fact Data Flows. This logical diagram also makes the intentionally unwritten unchanged route explicit.',maxheight=4.5),
 p('Upsert means insert a missing key or update an existing one. Lookup of the warehouse fact key is separate from the earlier dimension key checks. Product_Id identifies a stock fact; source line Id identifies a purchase fact.'),
 p('The no-match path uses an OLE DB Destination for new rows. The match path enters a Conditional Split that compares every stored attribute or measure using NULL-safe expressions. Changed rows reach an OLE DB Command with parameterized UPDATE SQL. Equal rows require no warehouse write.'),
 p('The stock comparison covers DateKey, quantity, threshold and alert. The purchase comparison covers document, date, product, supplier, quantity and amount. Destination fast load uses CHECK_CONSTRAINTS so the SQL foreign keys remain enforced and trusted.'),
 p('An OLE DB Command runs a parameterized SQL command for an input row. This approach follows the original supplier/payment style and is easy to inspect in the designer. It is not a claim that row-by-row updates are the most scalable design for every production warehouse.'))

page('25 Calculate net purchase amounts correctly',
 p('PrixTotalHt is the line HT amount after its own line discounts. Some invoices also have a document-level discount. Summing the lines without applying that global adjustment would overstate net purchases. In this dataset, 53 validated invoices differ between their line HT sum and header TotalNetHt by more than 0.01.'),
 h('Proportional allocation rule'),
 p('For an invoice, let S be the sum of commercial line HT amounts and N be the header TotalNetHt. Each line receives its share of N in proportion to its original line amount. The proportion is represented to eight decimal places, and each line amount is rounded to four decimal places. The residual needed to reach exactly N is assigned to the commercial line with the greatest source Id.'),
 table(['Fictional line','Base HT','Share of invoice net HT','Result'],[
 ('Line 101','120.0000','120 / 200 of 180','108.0000'),('Line 102','80.0000','80 / 200 of 180','72.0000'),('Invoice','200.0000','Net header 180.0000','180.0000'),
 ],[1.5,1.35,2.65,1.35]),
 p('The allocated document discount is the original line HT minus its final net share. The visible SSIS Derived Column then calculates the warehouse amount by subtracting that share of document discount. The discount is not applied twice.'),
 code('MontantAchat_HT = (DT_NUMERIC,18,4)\n    ([TotalHt] - [RemiseDocument_HT])'),
 p('If S and N are both zero, original line values are preserved. If a nonzero net header cannot be allocated from the available line amounts, the calculated amount is missing and a validated commercial line fails the mandatory-value guard. It is not silently accepted with a fabricated amount.'))

page('26 Rounding and purchase field lineage',
 p('Rounding residual means the small difference between a required total and the sum of separately rounded parts. For example, three base lines of 1.0000 with invoice net 1.0000 produce three provisional shares of 0.3333. Their sum is 0.9999. Adding 0.0001 to the line with the greatest source Id gives 0.3334, 0.3333 and 0.3333, totaling exactly 1.0000.'),
 table(['Warehouse field','Origin or rule'],[
 ('Id','DocumentItem.Id converted to bigint; one row per source line'),
 ('Document_Id','Documents.Id; invoice reference retained in the fact'),
 ('DateKey','YYYYMMDD calculated from the explicitly parsed invoice date'),
 ('Product_Id','DocumentItem.ProductStock_Id to ProductStocks.Id to Product_Id'),
 ('Fournisseur_Id','Documents.Transaction_Id to Transactions.Id to Company_Id; -1 if unassigned'),
 ('QuantiteAchetee','Typed DocumentItem.Quantity'),
 ('MontantAchat_HT','Line PrixTotalHt minus allocated global discount, including rounding correction'),
 ],[1.65,5.2]),
 p('The warehouse holds 6964 eligible lines belonging to 880 invoices. The base line HT sum is 964358.5720; net purchases after document adjustments are 958947.7230. The difference is 5410.8490. The final assertions reconcile every invoice individually, so agreement is stronger than a coincidentally matching grand total.'),
 p('These amounts are net of discounts but exclude supplier credit notes. They are therefore not a net-after-returns purchase measure. No currency unit has been invented in this guide. Unit prices, TTC tax-inclusive amounts and cash settlements are not additional measures in this fact.'))

page('27 What happens when the load runs again',
 p('Idempotence means the same input produces the same final business tables after another execution. Here the source staging snapshot is refreshed, the calendar inserts only missing dates, dimensions follow SCD type 1, and existing facts are compared before an update.'),
 fig('reclassify','A source change can remove a fact as well as update its measures. The regression test reverses the change and verifies exact restoration.',maxheight=3.05),
 p('An upsert by itself cannot remove a line that has become ineligible. The preparation procedure therefore deletes stale keys before the native fact flows. When a source invoice changes from validated to draft, all its purchase fact lines are removed. Its candidate rows then follow the draft exclusion route. If it becomes validated again, its commercial line identifiers follow INSERT.'),
 p('For stock, a product no longer present in the current stock candidates is removed from the current snapshot fact. Dimensions are different: the SCD type-1 flows do not automatically purge a dimension member when it disappears from source. This keeps the final implementation’s deletion policy explicit.'),
 p('The tests compare hashes of every final dimension and fact before and after the second full Master execution. They also change destination values and a source invoice state to demonstrate repair, deletion and reinsertion rather than checking only a first successful load.'))

page('28 Validation and the meaning of 67 checks',
 p('The recorded suite has 67 successful checks and zero failures. These are script assertions and execution checks, not 67 unrelated unit-test functions. Several checks verify entire tables. Appendix C lists every recorded check by name.'),
 table(['Check family','Count','Evidence'],[
 ('Native package execution','6','Two full Masters and four focused ETL executions'),('Staging source row counts','17','Each raw staging table equals its manifest count'),
 ('Staging cell hashes','17','All parsed source cells and duplicate rows reconcile'),('Second-run table stability','7','Same keys and attributes in all seven warehouse tables'),
 ('Dimension repair and resulting table stability','7','Three NULL labels and a changed payment name are repaired'),('Known-threshold fixture prerequisite','1','The NULL stock test targets an actually known threshold'),
 ('Fact UPDATE repair','2','Stock and purchase hashes return to baseline'),('Reclassified invoice removal','1','No fact line remains for the temporary draft invoice'),
 ('Restoration after source fixture','7','All seven tables match the original baseline again'),('SQL reconciliation and FK checks','1','Both fact directions, headers, calendar and trusted keys'),
 ('Warehouse table population','1','The report records five dimensions and two facts'),
 ],[2.55,.55,3.75]),
 p('SHA256 is a cryptographic hash used here as a compact fingerprint, not encryption. Each cell is represented with its UTF16 byte length followed by its bytes. Each row is hashed; row hashes are sorted with duplicate occurrences retained; the complete sorted list is hashed again. This multiset comparison ignores SQL row order while preserving duplicate counts.'),
 p('CSV empty cells and SQL NULL are treated equivalently in this cell check. Original file byte hashes are recorded separately. Hash agreement supports transfer fidelity under that defined normalization; it does not certify that an absent product description is factually known.'))

page('29 Final SQL assertions and recorded results',
 p('The final Verification task requires exactly the seven intended warehouse tables. It checks calendar size and attributes, special dimension members, required descriptions, six payment modes, and enabled trusted foreign keys. A trusted FK has been validated against existing rows; it is more than a constraint name stored in metadata.'),
 p('For each fact, the SQL uses differences in both directions: source candidates minus loaded facts and loaded facts minus source candidates. Keys and measures must agree, not just row counts. The purchase check also groups loaded facts by invoice and requires the sum of MontantAchat_HT to equal source TotalNetHt exactly.'),
 ('results',),
 p('The stock total is 18800.0000. There are 4449 known thresholds, 2393 unknown thresholds and 2195 products below their known threshold. Purchase net HT is 958947.7230 over 880 invoices. The exclusion log ends with 49 draft lines and 14 no-product comment lines. Five foreign keys are enabled and trusted.'),
 p('The measured product dimension still contains 2182 explicit unknown labels, 2543 unknown families and 3055 unknown brands. These figures describe missing or unmatched source descriptions. Integration success does not turn an unknown source value into verified business knowledge.'),
 p('The evidence files are verification-results.json, implementation-summary.json, source-manifest.json, build.log, master.log, master-rerun.log, dimension-null-and-update.log, facts-update.log, facts-source-reclassification.log, facts-source-restored.log and sql-validation.log in reports. FINAL-REPORT.md is the human-readable summary.'))

page('30 Run the project on the current machine',
 h('Open and execute in Visual Studio'),
 p('Open HealthRetailers_SSIS.sln from the HealthRetailers_DW_amal folder. If Visual Studio reports that package files changed outside the editor, reload them. Open Master.dtsx to see staging, calendar, warehouse loading and verification. Execute Master as the entry package. The required runtime has already been installed on this machine.'),
 p('To inspect transformations, open ETL_SA_DW.dtsx and double-click a task named alim_dim_client, alim_dim_produit, alim_dim_fournisseur, alim_dim_paiement, alim_fait_stock_actuel or alim_fait_achats. The first four are the retained dimension diagrams; the final two are the added fact flows.'),
 h('View the SQL data'),
 p('In SSMS, connect to localhost with Windows Authentication. Expand Databases, then SA_Health_Dimensions for staging or DW_Health_Dimensions for the warehouse. Refresh Object Explorer if a newly created table is not yet visible. SSMS can be closed while a package runs.'),
 code('USE DW_Health_Dimensions;\nSELECT COUNT(*) FROM dbo.fait_stock_actuel;\nSELECT COUNT(*) FROM dbo.fait_achats;'),
 h('Run through the supplied scripts'),
 code('powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\\setup.ps1\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\\verify.ps1'),
 p('Run the commands from the HealthRetailers_DW_amal project folder. setup.ps1 is for setup or intentional reconfiguration; it is not required before every Master run. verify.ps1 runs the regression suite and temporarily modifies controlled fixtures before restoring them. Avoid concurrent manual package runs while that verification is executing. The normal operating entry point is Master, not the fixture tests.'))

page('31 Configure or move the project',
 p('settings.example.json records the default server and database names. Copy it to settings.json if a deliberate configuration change is needed, then run setup.ps1. configure.py reads the local settings, creates transport copies, replaces connection paths and changes the project target to SQL Server 2022.'),
 code('{\n  "Server": "localhost",\n  "StagingDatabase": "SA_Health_Dimensions",\n  "WarehouseDatabase": "DW_Health_Dimensions"\n}'),
 p('There is no implemented SSIS project parameter named DossierDonnees. Paths are configured by the supplied setup process. Database connection managers and the added fact package connections use integrated Windows authentication.'),
 p('A solution file, .sln, groups the project for Visual Studio. The .dtproj file defines the SSIS project and target version. A .dtsx file stores a package. A .conmgr file stores a connection manager. The build produces HealthRetailers_SSIS.ispac under HealthRetailers_SSIS/bin/Development, a compiled project deployment artifact used by DTExec.'),
 p('The raw business data and transport copies are excluded from Git. A fresh clone on another machine therefore also needs the source files listed in scripts/sources.json under data/original. The current machine already has them. configure.py can use the adjacent original repository as a local fallback; that fallback is not an internet download service.'),
 p('The required environment is SQL Server 2022, full SSIS 2022 runtime, Visual Studio 2022 with the SSIS Projects extension, the Microsoft OLE DB SQL Server provider, Python and sqlcmd. The C# authoring helper uses installed SSIS assemblies during setup; the saved runtime flows use native SSIS components.'))

page('32 Analyse the warehouse in SSMS',
 p('sql/07_analyses.sql contains read-only examples. To run the file directly in SSMS, enable SQLCMD Mode and define the variable with :setvar WarehouseDatabase DW_Health_Dimensions. The queries below can also run directly in the warehouse database. Analysis should respect the grain and unknown values. Product family or brand joins come from dim_produit; month and supplier joins come from dim_temps and dim_fournisseur.'),
 h('Find products that need attention'),
 code('SELECT p.Product_Id, p.Libelle,\n       f.QuantiteActuelle, f.QuantiteAlerte\nFROM dbo.fait_stock_actuel f\nJOIN dbo.dim_produit p ON p.Product_Id = f.Product_Id\nWHERE f.EstSousSeuil = 1;'),
 p('This returns products below a known threshold. Products with unknown thresholds are not included by that predicate; report their count separately instead of assuming they need no action.'),
 h('Compare net purchases by month and supplier'),
 code('SELECT t.Annee, t.Mois, s.Nom,\n       SUM(f.MontantAchat_HT) AS MontantAchat_HT\nFROM dbo.fait_achats f\nJOIN dbo.dim_temps t ON t.DateKey = f.DateKey\nJOIN dbo.dim_fournisseur s\n  ON s.Fournisseur_Id = f.Fournisseur_Id\nGROUP BY t.Annee, t.Mois, s.Nom;'),
 p('This sums invoice-line net amounts after the document discount allocation. It excludes supplier credit notes by design. Quantities are better analysed by product or compatible units. Do not join a one-to-many payment table into this result without a separate allocation design.'))

page('33 Diagnose a failed execution',
 table(['Symptom','Likely interpretation','What to inspect'],[
 ('Database connection fails','Wrong server, permissions or provider setup.','settings files, connection managers, SQL Server availability'),
 ('Flat File Source fails','Path, encoding, delimiter, quoting or width issue.','Original/transport files, source manifest, flat-file manager'),
 ('Preparation reports invalid core values','A mandatory identifier, date, quantity or net amount is invalid.','v_source_stock, v_source_achats and the original raw rows'),
 ('Dimension Lookup reports no match','A required warehouse reference is absent.','Candidate key and its corresponding dimension member'),
 ('Conditional Split cannot evaluate','An expression did not yield a definite Boolean.','NULL handling and the exact compared columns'),
 ('Header totals do not reconcile','A line, discount or rounding rule disagrees with the invoice.','Line amounts, TotalNetHt and allocated residual'),
 ('A diagram is not visible','Master is open, or the file is being viewed as XML.','Open the SSIS designer and the Data Flow inside ETL_SA_DW'),
 ],[1.9,2.35,2.6]),
 p('Read the first specific error rather than only the final package-failure line. DTExec reports exit 0 for success and a nonzero result for failure. SQL validation uses THROW to produce explicit error messages. sql-validation.log may contain an aggregate NULL-elimination warning because unknown optional values are deliberately excluded from aggregates; that warning is not a failed assertion.'),
 p('The implementation does not promise an all-warehouse rollback for every possible failure. Raw staging is refreshed and parts of an unsuccessful run may have completed. Fix the source/configuration problem and rerun Master to restore the intended final state. The finally blocks in verification restore its controlled fixtures, but do not provide protection from a forced operating-system termination.'),
 p('The packages are intended for one coordinated local run at a time. Scheduling, multi-run concurrency control, production monitoring and backup policy are future operational work, not completed features.'))

page('34 Known limits and responsible interpretation',
 p('A completed integration means the implemented sources, transformations, schema and validation have run successfully. It does not mean the source is perfect, that every possible future change is covered, or that business owners have confirmed all inherited classifications.'),
 table(['Limit','Consequence'],[
 ('Stock capture date not established','DateKey remains NULL and no historical stock trend is claimed.'),
 ('Missing product descriptions or thresholds','Explicit unknown values remain visible; no guessed spelling or default threshold is presented as fact.'),
 ('Supplier credit notes excluded','Purchase amounts are net of discounts but not net of returns.'),
 ('French holiday logic inherited','The business must confirm the relevant country calendar.'),
 ('SCD type 1 dimension updates','Historical purchases use the current product family/name, not an old attribute version.'),
 ('Full file staging refresh','This is a snapshot-based file integration, not real-time change data capture.'),
 ('Local configuration and files','Another computer needs the runtime, source files and configured connections.'),
 ('No published remote update','The working changes are local; GitHub publication was not requested.'),
 ],[2.6,4.25]),
 p('No sales, receipt or supplier-payment fact is part of this final seven-table warehouse. Client and payment dimensions are retained because they are part of the group’s dimensional foundation and can support later facts. A fact is not required to connect to every available dimension.'),
 p('The 67 passing checks establish the recorded behavior on the supplied dataset: faithful raw transfer, stable reruns, native loading, tested repairs, source reclassification handling and reconciliation. They do not replace a business review of source semantics or guarantee a grade.'))

page('35 Explain the project to the teacher',
 h('A coherent demonstration order'),
 p('Start with the business questions: which products are below their stock threshold, and how much was purchased from each supplier by period? Show the architecture diagram, then the two real SQL databases. Define the grain of both facts before showing their measures.'),
 p('Open Master to explain orchestration. Open one raw staging Data Flow. Then show the product or client dimension with Sort and Merge Join, followed by the supplier Lookup pattern. Finally show the stock and purchase fact flows, including their INSERT and UPDATE branches.'),
 p('For purchases, explain the validated-invoice filter, comment exclusions, supplier unknown member, date conversion and global discount allocation. Show that each invoice’s net line sum equals its header. Finish with row counts, a simple analysis query and the verification report.'),
 h('Questions worth preparing'),
 table(['Question','Answer'],[
 ('Why have a Staging Area?','To preserve source evidence and separate receiving data from interpreting it.'),
 ('Why are the counts different?','Source rows and dimension/fact rows have different grains and eligibility rules.'),
 ('Why not use today as the stock date?','Processing time does not prove the date of the exported business snapshot.'),
 ('Why are payment and client not in these facts?','They support other business processes; these two facts do not need those keys.'),
 ('What happens on a second run?','Stable inputs produce identical final rows; new/changed keys follow INSERT/UPDATE.'),
 ('Is everything visual SSIS?','Warehouse row loading is native Data Flows; SQL handles setup, documented source preparation and assertions.'),
 ('What does a successful test not prove?','It does not recover missing business descriptions or certify all future production scenarios.'),
 ],[2.65,4.2]))

page('36 Implementation files and traceability',
 table(['File or folder','Role'],[
 ('HealthRetailers_SSIS.sln and .dtproj','Open/build the SSIS project for SQL Server 2022'),('EL_SI_SA.dtsx','Raw staging import'),('ETL_SA_DW.dtsx','Four dimension and two fact Data Flows plus preparation'),('Master.dtsx','Staging, calendar, loading and validation entry point'),
 ('sql/01_SA_Health.sql','Portable raw staging schema'),('sql/02_DW_Health.sql','Five dimension schemas'),('sql/03_alim_dim_temps.sql','Repeatable calendar generation used by Master'),('sql/04_dimension_sources.sql','Text helpers and product source procedure'),('sql/05_faits.sql','Two fact schemas, numeric helper, caches, views and preparation'),('sql/99_verifications.sql','Warehouse assertions embedded in Master'),('sql/07_analyses.sql','Read-only demonstration queries'),
 ('scripts/configure.py and sources.json','Transport preparation and local configuration'),('scripts/build-facts.ps1 and FactGraphs.cs','Generate native fact components and paths through the SSIS API'),('scripts/layout-facts.py','Restore original dimension layouts and lay out the two new fact graphs'),('scripts/setup.ps1','Configure, install SQL objects and build'),('scripts/verify.ps1','Run the measured validation and regression suite'),
 ],[3.2,3.65]),
 p('The guide’s diagrams are reconstructed from the actual package metadata and documented SQL behavior. Where a long flow is split into two explanatory diagrams, this is a presentation choice; the saved package still contains one connected Data Flow.'),
 p('The reproducible source of this guide is kept in docs/complete-guide. The package and SQL files, not this prose, are the execution authority. The following appendices expose every final warehouse field, raw source field inventory, recorded check and principal technical term.'))
