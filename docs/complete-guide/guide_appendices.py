from guide_content import p,h,table,code

DICTIONARY=[
 ('Product dimension fields','dim_produit',[
 ('Product_Id','int  PK  NOT NULL','Source ProductStocks product identifier; one member per product.'),
 ('Libelle','nvarchar(255)  NULL','Chosen catalogue, line or event description; explicit unknown fallback required by QA.'),
 ('Famille','nvarchar(100)  NOT NULL','Catalogue family or NON RENSEIGNE.'),('Marque','nvarchar(100)  NOT NULL','Catalogue brand, known prefix inference or NON RENSEIGNE.')]),
 ('Client dimension fields','dim_client',[
 ('Company_Id','int  PK  NOT NULL','Company identifier; includes -1 unknown and 2 anonymous.'),('Nom','nvarchar(200)  NULL','Cleaned customer name, company fallback or explicit special-member label.'),
 ('TypeClient','nvarchar(30)  NOT NULL','Known customer classification or NON RENSEIGNE.'),('EstClientIdentifie','bit  NOT NULL','0 for -1 and 2, otherwise 1 for retained customer identifiers.')]),
 ('Supplier dimension fields','dim_fournisseur',[
 ('Fournisseur_Id','int  PK  NOT NULL','Company/supplier identifier; -1 is the unknown member.'),('Nom','nvarchar(200)  NULL','Supplier-export or company name; explicit unknown fallback.')]),
 ('Payment mode dimension fields','dim_paiement',[
 ('PaymentMode_Id','int  PK  NOT NULL','Distinct source payment-mode identifier; -1 unknown.'),('PaymentModeName','nvarchar(50)  NOT NULL','Readable mapping of the application payment-mode label.')]),
 ('Calendar dimension fields','dim_temps',[
 ('DateKey','int  PK  NOT NULL','YYYYMMDD integer key.'),('Date','date  NOT NULL','Calendar date from 2024-09-30 to 2026-09-29.'),('Annee','smallint  NOT NULL','Calendar year.'),('Trimestre','tinyint  NOT NULL','Quarter 1 to 4.'),('Mois','tinyint  NOT NULL','Month 1 to 12.'),('SemaineISO','tinyint  NOT NULL','ISO week number.'),('EstFerie','bit  NOT NULL','Inherited French holiday indicator.')]),
 ('Current stock fact fields','fait_stock_actuel',[
 ('Product_Id','int  PK FK  NOT NULL','Current product snapshot key referencing dim_produit.'),('DateKey','int  FK  NULL','Optional reference to dim_temps; always NULL in this export-based version.'),
 ('QuantiteActuelle','decimal(18,4)  NOT NULL','Sum of source stock quantities at product grain.'),('QuantiteAlerte','decimal(18,4)  NULL','Known consistent threshold, otherwise NULL.'),('EstSousSeuil','bit  NULL','1 if quantity is below a known threshold; 0 if not; NULL if no threshold.')]),
 ('Purchase fact fields','fait_achats',[
 ('Id','bigint  PK  NOT NULL','Unique source DocumentItem line identifier.'),('Document_Id','bigint  NOT NULL','Invoice identifier retained as a document reference.'),('DateKey','int  FK  NOT NULL','Invoice date key referencing dim_temps.'),('Product_Id','int  FK  NOT NULL','Product reference from the line’s stock identifier.'),('Fournisseur_Id','int  FK  NOT NULL','Supplier reference from the invoice transaction; -1 when unassigned.'),('QuantiteAchetee','decimal(18,4)  NOT NULL','Source line quantity.'),('MontantAchat_HT','decimal(18,4)  NOT NULL','Line HT after its allocated document discount and residual correction.')]),
]

GLOSSARY=[
 ('Aggregate','Combine several values at a chosen grain, for example SUM of stock quantities per product.'),
 ('Assertion','An executable condition that must be true. The final SQL assertions throw an error when a required condition fails.'),
 ('Bigint','SQL Server integer type used here for document and invoice-line identifiers.'),
 ('Binary collation','Text comparison based on exact character values. Used for reliable corruption-character detection.'),
 ('Bit','SQL Boolean-like storage with values 0 or 1; a nullable bit can also be NULL.'),
 ('BOM','Byte order mark, an optional encoding marker at the start of a text file. The decoding logic handles UTF8 with an optional BOM.'),
 ('Business key','Identifier originating in the business application, such as Product_Id. Existing business identifiers are used as dimension keys here.'),
 ('Cache','Prepared data kept for repeated lookup. The two staging caches are rebuilt each load and do not replace the raw evidence.'),
 ('Cardinality','How many records can participate in a relationship. Stock currently permits at most one fact row per product.'),
 ('CI AI','Case-insensitive and accent-insensitive collation behavior. Used for matching labels without requiring identical case or accent marks.'),
 ('Clone','A local copy of a Git repository, including its history and available remote references.'),
 ('Collation','Rules SQL Server applies when comparing or sorting text, including case and accent sensitivity.'),
 ('Conditional Split','SSIS transformation that routes a row according to a Boolean expression. It does not itself change the database.'),
 ('Conformed dimension','A shared, consistently defined dimension. Product and date are reused by the final facts.'),
 ('Connection manager','SSIS definition of how to access a file or database. Project managers are stored as .conmgr files.'),
 ('Control Flow','Package-level task orchestration. Its arrows establish execution conditions rather than carrying table rows.'),
 ('Credit note','Document that reverses or adjusts an invoice. Supplier credit notes are type 23 and are excluded from the delivered purchase fact.'),
 ('CSV','Delimited text records. These exports use commas or semicolons with configured quotation rules.'),
 ('CTE','Common table expression, a named query expression used within a SQL statement. The purchase view uses CTEs to explain staged calculations.'),
 ('Data Flow','The SSIS row-processing graph containing sources, transformations and destinations.'),
 ('Data lineage','The trace from an output field back to its source fields and transformation rules.'),
 ('Data warehouse','Database organized to support business analysis. The final database has five dimension tables and two fact tables.'),
 ('DateKey','Integer calendar key in YYYYMMDD format. It is different from a free-text date label.'),
 ('Decimal precision and scale','decimal(18,4) stores 18 total digits, four after the decimal point. It avoids binary floating-point storage for the fact measures.'),
 ('Derived Column','SSIS transformation that adds or replaces a value using an expression, such as date key, selection reason or net amount.'),
 ('Dimension','Descriptive table used to analyse facts, for example product family or supplier name.'),
 ('Draft','A source document that is not validated. State 0 invoices do not contribute purchase facts.'),
 ('DTExec','Microsoft command-line utility used to execute the built SSIS project and return an execution result.'),
 ('Encoding','Rule mapping characters to file bytes. UTF8, UTF16 and CP1252 are different encodings encountered in this project.'),
 ('ETL','Extract, Transform, Load. Reading the exports, interpreting their fields and storing the warehouse records form this pipeline.'),
 ('EXCEPT','SQL set-difference operator. Used in both directions to find source-only and warehouse-only fact rows.'),
 ('Execute Package task','Control Flow task that calls another .dtsx package from the project.'),
 ('Execute SQL task','Control Flow task that runs SQL, such as calendar generation, preparation or validation.'),
 ('Fact constellation','Several fact tables sharing conformed dimensions. This describes the product/date sharing in the small final model.'),
 ('Fact table','Table storing observations and measures at an explicit grain, with references to relevant dimensions.'),
 ('Fixture','A controlled temporary change introduced by a test, then restored. It is not a new production business record.'),
 ('Flat File Source','SSIS source component that reads delimited text using a connection manager.'),
 ('Foreign key','Reference that requires a matching parent key, unless the referencing column permits NULL.'),
 ('GO','Batch separator recognized by tools such as sqlcmd and SSMS. It is not a SQL instruction to send unchanged inside an Execute SQL task.'),
 ('Grain','The precise level of detail of one row, such as one invoice line or one current product stock balance.'),
 ('Hash','A compact deterministic fingerprint of content. It is used for comparison, not for recovering missing source characters.'),
 ('HTML','Markup embedded in some descriptions. Tags and selected entities are cleaned where product source logic requires it.'),
 ('HT','Hors taxes, the amount excluding tax. MontantAchat_HT is net of document discounts in this implementation.'),
 ('Idempotence','Repeated execution with the same inputs leads to the same final business-table contents.'),
 ('Index','SQL access structure that helps repeated searches. The technical code cache has a primary-key index and the threshold cache has lookup indexes.'),
 ('Integration Services runtime','The installed SSIS execution components. A database engine connection alone is not enough to execute every SSIS package.'),
 ('Invoice header','Document-level record containing date, supplier transaction link, status and totals.'),
 ('Invoice line','A product or comment row associated with a document. Its source Id defines the purchase fact key.'),
 ('JSON','Structured text with named values. Product events contain id, cde and lbl evidence.'),
 ('Lookup','SSIS key search against a reference dataset. No-match can be redirected for insertion or configured to fail for a required dimension.'),
 ('Manifest','Inventory of source files, columns, expected counts, encodings and fingerprints.'),
 ('Measure','Quantitative fact value that can be analysed at its defined grain. Additivity depends on the measure and dimensions.'),
 ('Merge Join','SSIS transformation that combines two sorted rowsets by a join key. Used by the retained product and client dimension flows.'),
 ('Mojibake','Text damaged by a wrong encoding interpretation, sometimes repairable from a known byte/character sequence.'),
 ('Multiset','Collection that retains repeated occurrences. The cell-hash comparison keeps duplicate row counts while ignoring ordering.'),
 ('Natural key','Another name for a business-origin identifier, contrasted with an independently generated surrogate key.'),
 ('NULL','Missing or unknown SQL value. It is different from zero; normal comparisons involving NULL may yield unknown.'),
 ('NULLIF','SQL function returning NULL when two expressions are equal. It converts trimmed empty identifier strings to missing values before numeric conversion.'),
 ('NVARCHAR','SQL Server Unicode text type. The raw staging uses it to preserve decoded characters.'),
 ('OLE DB','Database access interface used by native SSIS sources, destinations, lookups and commands.'),
 ('OLE DB Command','SSIS transformation that executes a parameterized SQL command for each input row. Used for the explicit UPDATE paths.'),
 ('OLE DB Destination','SSIS component writing input rows into a SQL target table. Fast load is used with constraint checking.'),
 ('OLE DB Source','SSIS component that reads a table, view or SQL query and produces pipeline rows.'),
 ('Orphan reference','Fact key with no corresponding dimension row. Required Lookups and foreign keys prevent these from being silently loaded.'),
 ('PK','Primary key. The unique non-NULL identifier of a table row.'),
 ('Precedence constraint','Control Flow connector determining whether a task may run, normally after predecessor success here.'),
 ('Proportional allocation','Distribute a document-level amount according to line shares. Used for global purchase discounts.'),
 ('Reconciliation','Compare source and loaded keys or measures so differences are explicit. Invoice totals are reconciled separately.'),
 ('Replacement character','U+FFFD marker indicating a character could not be represented during an earlier decoding step. It is not the original missing letter.'),
 ('Rounding residual','Difference between a required total and the sum of separately rounded parts. Assigned to one deterministic commercial line here.'),
 ('ROW NUMBER','SQL window function that numbers rows within a group. It chooses latest events and the deterministic residual line.'),
 ('SCD type 1','Slowly Changing Dimension behavior that overwrites an old attribute rather than keeping an attribute-history version.'),
 ('SHA256','Hash algorithm used for original file bytes, row values and table comparisons in the recorded checks.'),
 ('Snapshot','An observation of a state at a point in time. The supplied stock capture date is unknown; the fact stores current source state only.'),
 ('Sort','SSIS transformation called Trier that orders input rows before the client/product Merge Joins.'),
 ('SQLCMD Mode','SSMS mode that accepts script variables and batch tooling conventions used by the setup scripts.'),
 ('SSIS','SQL Server Integration Services, the package and Data Flow integration platform used by this project.'),
 ('SSMS','SQL Server Management Studio, a database administration and querying client.'),
 ('Staging Area','Intermediate data layer between source exports and warehouse tables. It holds raw rows and technical preparation here.'),
 ('Star schema','A fact table linked to descriptive dimensions. Each final fact forms a small star.'),
 ('Stored procedure','Named SQL routine installed inside a database. Product matching and fact preparation are procedures here.'),
 ('Surrogate key','Artificial warehouse-generated identifier independent of the source business key. This version retains business keys instead.'),
 ('Text qualifier','Character identifying a quoted CSV cell. Double quotation marks protect embedded delimiters and JSON quotes.'),
 ('Trusted foreign key','Constraint whose existing data has also been validated. Fast-load constraint checking preserves this state.'),
 ('TRY CAST and TRY CONVERT','SQL conversions returning NULL on a conversion failure, allowing an explicit subsequent quality decision.'),
 ('TTC','Toutes taxes comprises, a tax-inclusive amount. It is not the purchase fact’s HT measure.'),
 ('Unicode','Character system supporting accented and multilingual text; UTF8 and UTF16 are encodings used to represent it.'),
 ('Unknown member','A real dimension row representing an unassigned reference, typically key -1 here. It differs from inventing an actual supplier.'),
 ('Upsert','Insert a missing key or update the values of an existing key.'),
 ('Validation','Executable checking of defined rules. It is not proof that every source business value is known or that all future scenarios are covered.'),
 ('View','Saved SQL query definition that exposes candidate rows without itself storing a separate copy of those rows.'),
 ('Window function','SQL calculation over related rows while retaining the individual row grain, such as an invoice total beside each line.'),
 ('Windows Authentication','SQL connection using the Windows identity rather than embedding a SQL username and password.'),
 ('Working branch','Local Git line of work. The final changes remain on codex/fix-five-dimensions unless deliberately published later.'),
]

GLOSSARY += [
 ('API','Application programming interface. The authoring scripts use the SSIS API to create native package objects programmatically.'),
 ('Boolean','A true-or-false value. SSIS Conditional Split expressions must produce a definite Boolean rather than NULL.'),
 ('Column','A named field shared by the rows of a table, such as Quantity.'),
 ('CP1252','Windows character encoding used by three selected source files in the recorded manifest.'),
 ('Database','Organized collection of tables and other objects managed by the SQL Server engine.'),
 ('Database instance','Running SQL Server service addressed by a server name. The configured instance is localhost.'),
 ('DDL','Data definition language, the SQL statements that create or change schemas, tables, keys, views and routines.'),
 ('Delimiter','Character separating CSV fields, a comma or semicolon in the selected exports.'),
 ('DT I4 and DT BOOL','SSIS expression types: a four-byte integer and a Boolean. Used by NULL(DT_I4) and NULL(DT_BOOL).'),
 ('DT NUMERIC and DT WSTR','SSIS exact numeric and Unicode string types used in Derived Column casts.'),
 ('File extensions','Suffixes identifying artifact formats: .sln solution, .dtproj SSIS project, .dtsx package, .conmgr connection and .ispac compiled project.'),
 ('Metadata','Information describing data, such as column names, data types and pipeline component connections.'),
 ('Nullable','A column is nullable when its schema permits NULL. Business validation may impose an additional nonempty-value requirement.'),
 ('Parameter','Value supplied separately to a command. OLE DB Command uses placeholders and mapped row values for updates.'),
 ('Parsing','Reading a representation according to its structure, such as CSV quoting rules or JSON field names.'),
 ('Query','Request to retrieve or calculate data, usually expressed in SQL here.'),
 ('Referential integrity','Consistency between referencing fact keys and their parent dimension keys.'),
 ('Row','One record in a table or SSIS pipeline. Its business meaning is determined by the grain.'),
 ('Schema','The defined structure of database objects and fields. The dbo schema namespace contains the final tables.'),
 ('SDK','Software development kit. Installed SSIS assemblies provide the authoring objects used by the setup helpers.'),
 ('SQL','Structured Query Language, used to define objects, retrieve candidates, prepare sources, update records and validate results.'),
 ('Table','A stored set of rows sharing named typed columns. Views expose queries; tables store the records.'),
 ('Ternary expression','An expression choosing one value when a condition is true and another when false, written condition ? yes : no in SSIS.'),
 ('Transaction','A coordinated database work unit in SQL, or a business transaction in the source application. Transactions_SA stores the latter; the complete ETL is not promised to roll back as one atomic SQL transaction.'),
]
GLOSSARY.sort(key=lambda x:x[0].casefold())

TECHNICAL_STAGING=[
 h('Technical staging tables'),
 p('The 17 raw tables are supplemented by three technical tables. These prepared or diagnostic records do not replace the original source evidence.'),
 table(['Object','Fields and types'],[
 ('Rejets_Faits','Fait nvarchar(40) NOT NULL; SourceId bigint NULL; Motif nvarchar(100) NOT NULL. Stores the excluded candidate line and its reason.'),
 ('CatalogueSeuils_Faits','Code nvarchar(200) NULL; Libelle nvarchar(255) NULL under CI_AI collation; Seuil decimal(18,4) NULL. Indexed by code and label.'),
 ('CodesProduits_Faits','Product_Id int PRIMARY KEY NOT NULL; Code nvarchar(200) NULL. One latest product-event code per product identifier.'),
 ],[2.1,4.75]),
 h('Candidate view outputs'),
 p('v_source_stock returns Product_Id, QuantiteActuelle and QuantiteAlerte. The Data Flow adds DateKey and EstSousSeuil.'),
 p('v_source_achats returns Id, Document_Id, DocumentDate, IsValidated, Product_Id, Fournisseur_Id, Quantity, TotalHt, RemiseDocument_HT and MontantNet_HT. Intermediate invoice totals and row numbers are used within the SQL calculation without changing the invoice-line grain.'),
 p('Both caches are rebuilt by usp_preparer_faits. Rejets_Faits is cleared for the next run after mandatory-value guards succeed, then populated by the purchase exclusion branch.'),
]

def appendices(manifest,checks):
 pages=[]
 # Seven complete warehouse dictionaries, grouped to remain readable.
 for i in range(0,len(DICTIONARY),2):
  blocks=[p('These are the implemented fields and types. PK means primary key, FK means foreign key. NULL is a permitted physical value; the final validation can impose a stronger business requirement.')]
  for heading,name,rows in DICTIONARY[i:i+2]:blocks += [h(heading),p('SQL table '+name),table(['Field','Type and key','Lineage and meaning'],rows,[1.45,1.8,3.6])]
  pages.append(('Appendix A Warehouse field dictionary '+str(i//2+1),blocks))
 # Complete source field inventory. Use actual target order, which is mapped from source order.
 for i in range(0,len(manifest),4):
  blocks=[p('Every listed field is retained as raw Unicode text. Names match the staging schema; source/target ordering and connections are configured in scripts/sources.json. UsersSettings.Value uses NVARCHAR(MAX); the other raw fields use NVARCHAR(4000).')]
  for s in manifest[i:i+4]:
   blocks += [h(s['table'].replace('_',' ')),p('File '+s['source']+' | '+str(s['rows'])+' rows | separator '+repr(s['delimiter'])+' | decoding '+s['encoding']),p('Fields: '+', '.join(s['columns'])+'.')]
  if i==16:blocks += TECHNICAL_STAGING
  pages.append(('Appendix B Raw source fields '+str(i//4+1),blocks))
 for i in range(0,len(checks),18):
  rows=[]
  for n,c in enumerate(checks[i:i+18],i+1):rows.append((str(n),c['Check'],'PASS' if c['Passed'] else 'FAIL'))
  pages.append(('Appendix C Recorded checks '+str(i//18+1),[p('Exact check labels from reports/verification-results.json. The final entry records the seven loaded table counts; the aggregate SQL check includes row/measure reconciliation and trusted foreign keys.'),table(['No','Recorded check','Result'],rows,[.45,5.5,.9])]))
 for i in range(0,len(GLOSSARY),12):
  pages.append(('Appendix D Technical terms '+str(i//12+1),[p('Definitions describe the term and, where useful, its role in this implementation.'),table(['Term','Definition'],GLOSSARY[i:i+12],[1.7,5.15])]))
 pages.append(('Appendix E Evidence and reading order',[
  p('Primary implementation base: https://github.com/amal-mh/HealthRetailers_DW at upstream commit 3d52d4f48c66da6eccee05ee1050188ae1a4af6d. Original wider project: https://github.com/Youssef-ben-ali/DataWarehouseProject_3AI4. The final runtime project is the local corrected Amal-based copy, not an assertion about either remote repository’s current deployed state.'),
  p('Current local project: C:\\Users\\firas\\OneDrive\\Documents\\ssis\\HealthRetailers_DW_amal. Final source code and packages are referenced by their relative filenames throughout this guide. The adjacent original project remains a separate historical implementation.'),
  p('For a first reading, follow chapters 1 to 11 to understand purpose and structure, then the relevant dimension and fact chapters. Use chapters 28 and 29 for evidence, chapters 30 to 33 for operation, and the appendices for exact fields and vocabulary.'),
  p('This guide is an English explanation of the final implemented scope, assembled from package XML, SQL definitions, the source manifest and recorded validation results. Diagrams are reconstructed documentation rather than screenshots. Fictional worked examples are explicitly labelled; reported business totals are measured.'),
  p('No production database credentials, private customer-row listings or invented missing source descriptions are needed to understand the process. The guide does not alter the packages, source data or SQL databases. The operational scripts remain the authority for execution.'),
 ]))
 return pages
