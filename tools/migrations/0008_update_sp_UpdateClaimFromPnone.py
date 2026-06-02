from django.db import migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('tools', '0007_set_managed_to_true'),
    ]

    operations = [
        migrations.RunSQL(
            """
            
            CREATE OR ALTER PROCEDURE [dbo].[uspUpdateClaimFromPhone]
            
                --@FileName NVARCHAR(255),
                @XML XML,
                @ByPassSubmit BIT = 0
                
                
            

            /*
            -1	-- Fatal Error
            0	-- All OK
            1	--Invalid HF CODe
            2	--Duplicate Claim Code
            3	--Invald CHFID
            4	--End date is smaller than start date
            5	--Invalid ICDCode
            6	--Claimed amount is 0
            7	--Invalid ItemCode
            8	--Invalid ServiceCode
            9	--Invalid Claim Admin
            */
            AS
            BEGIN	
            
                SET ANSI_NULLS ON
            
                SET QUOTED_IDENTIFIER ON
                
                SET XACT_ABORT ON

                --DECLARE @XML XML
                
                DECLARE @Query NVARCHAR(3000)

                DECLARE @ClaimID INT
                DECLARE @ClaimDate DATE
                DECLARE @HFCode NVARCHAR(8)
                DECLARE @ClaimAdmin NVARCHAR(8)
                DECLARE @ClaimCode NVARCHAR(50)
                DECLARE @CHFID NVARCHAR(50)
                DECLARE @StartDate DATE
                DECLARE @EndDate DATE
                DECLARE @ICDCode NVARCHAR(6)
                DECLARE @Comment NVARCHAR(MAX)
                DECLARE @Total DECIMAL(18,2)
                DECLARE @ICDCode1 NVARCHAR(6)
                DECLARE @ICDCode2 NVARCHAR(6)
                DECLARE @ICDCode3 NVARCHAR(6)
                DECLARE @ICDCode4 NVARCHAR(6)
                DECLARE @VisitType CHAR(1)
                DECLARE @GuaranteeId NVARCHAR(50)
                DECLARE @Program NVARCHAR(100)
                DECLARE @programId INT
                

                DECLARE @HFID INT
                DECLARE @ClaimAdminId INT
                DECLARE @InsureeID INT
                DECLARE @ICDID INT
                DECLARE @ICDID1 INT
                DECLARE @ICDID2 INT
                DECLARE @ICDID3 INT
                DECLARE @ICDID4 INT
                DECLARE @TotalItems DECIMAL(18,2) = 0
                DECLARE @TotalServices DECIMAL(18,2) = 0

                DECLARE @isClaimAdminRequired BIT = (SELECT CASE Adjustibility WHEN N'M' THEN 1 ELSE 0 END FROM tblControls WHERE FieldName = N'ClaimAdministrator')
                DECLARE @isClaimAdminOptional BIT = (SELECT CASE Adjustibility WHEN N'O' THEN 1 ELSE 0 END FROM tblControls WHERE FieldName = N'ClaimAdministrator')
                
                BEGIN TRY
                    
                        IF NOT OBJECT_ID('tempdb..#tblItem') IS NULL DROP TABLE #tblItem
                        CREATE TABLE #tblItem(ItemCode NVARCHAR(6),ItemPrice DECIMAL(18,2), ItemQuantity INT)

                        IF NOT OBJECT_ID('tempdb..#tblService') IS NULL DROP TABLE #tblService
                        CREATE TABLE #tblService(ServiceCode NVARCHAR(6),ServicePrice DECIMAL(18,2), ServiceQuantity INT)
                        
                        IF OBJECT_ID('tempdb..#tblServiceItems') IS NOT NULL DROP TABLE #tblServiceItems
                        CREATE TABLE #tblServiceItems(ServiceCode NVARCHAR(6),SubItemCode NVARCHAR(6),QtyAsked INT,PriceAsked DECIMAL(18,2))

                        IF OBJECT_ID('tempdb..#tblServiceServices') IS NOT NULL DROP TABLE #tblServiceServices
                        CREATE TABLE #tblServiceServices(ServiceCode NVARCHAR(6),SubServiceCode NVARCHAR(6),QtyAsked INT,PriceAsked DECIMAL(18,2))

                        --SET @Query = (N'SELECT @XML = CAST(X as XML) FROM OPENROWSET(BULK '''+ @FileName +''',SINGLE_BLOB) AS T(X)')
                        
                        --EXECUTE SP_EXECUTESQL @Query,N'@XML XML OUTPUT',@XML OUTPUT

                        SELECT
                        @ClaimDate = Claim.value('(ClaimDate)[1]','DATE'),
                        @HFCode = Claim.value('(HFCode)[1]','NVARCHAR(8)'),
                        @ClaimAdmin = Claim.value('(ClaimAdmin)[1]','NVARCHAR(8)'),
                        @ClaimCode = Claim.value('(ClaimCode)[1]','NVARCHAR(50)'),
                        @CHFID = Claim.value('(CHFID)[1]','NVARCHAR(50)'),
                        @StartDate = Claim.value('(StartDate)[1]', 'DATE'),
                        @EndDate = Claim.value('(EndDate)[1]','DATE'),
                        @ICDCode = Claim.value('(ICDCode)[1]','NVARCHAR(6)'),
                        @Comment = Claim.value('(Comment)[1]','NVARCHAR(MAX)'),
                        @Total = CASE Claim.value('(Total)[1]','VARCHAR(10)') WHEN '' THEN 0 ELSE CONVERT(DECIMAL(18,2),ISNULL(Claim.value('(Total)[1]','VARCHAR(10)'),0)) END,
                        @ICDCode1 = Claim.value('(ICDCode1)[1]','NVARCHAR(6)'),
                        @ICDCode2 = Claim.value('(ICDCode2)[1]','NVARCHAR(6)'),
                        @ICDCode3 = Claim.value('(ICDCode3)[1]','NVARCHAR(6)'),
                        @ICDCode4 = Claim.value('(ICDCode4)[1]','NVARCHAR(6)'),
                        @VisitType = Claim.value('(VisitType)[1]','CHAR(1)'),
                        @GuaranteeId = Claim.value('(GuaranteeNo)[1]','NVARCHAR(50)'),
                        @Program = Claim.value('(Program)[1]', 'NVARCHAR(100)')
                        FROM @XML.nodes('Claim/Details')AS T(Claim)
                        
                        -- Correction temporaire du nom de programme -----------------------------------------------------
                        -- IF @Program = N'Chèque Santé'
                        --    SET @Program = N'Cheque Santé'


                        INSERT INTO #tblItem(ItemCode,ItemPrice,ItemQuantity)
                        SELECT
                        T.Items.value('(ItemCode)[1]','NVARCHAR(6)'),
                        CONVERT(DECIMAL(18,2),T.Items.value('(ItemPrice)[1]','DECIMAL(18,2)')),
                        CONVERT(DECIMAL(18,2),T.Items.value('(ItemQuantity)[1]','NVARCHAR(15)'))
                        FROM @XML.nodes('Claim/Items/Item') AS T(Items)



                        INSERT INTO #tblService(ServiceCode,ServicePrice,ServiceQuantity)
                        SELECT
                        T.[Services].value('(ServiceCode)[1]','NVARCHAR(6)'),
                        CONVERT(DECIMAL(18,2),T.[Services].value('(ServicePrice)[1]','DECIMAL(18,2)')),
                        CONVERT(DECIMAL(18,2),T.[Services].value('(ServiceQuantity)[1]','NVARCHAR(15)'))
                        FROM @XML.nodes('Claim/Services/Service') AS T([Services])
                        
                        
                        
                        -- SUB ITEMS
                        INSERT INTO #tblServiceItems(ServiceCode, SubItemCode, QtyAsked, PriceAsked)
                        SELECT
                            P.value('(ServiceCode)[1]', 'NVARCHAR(6)'),
                            S.value('(SubItemCode)[1]', 'NVARCHAR(6)'),
                            CONVERT(INT, S.value('(QtyAsked)[1]', 'INT')),
                            CONVERT(DECIMAL(18,2), S.value('(PriceAsked)[1]', 'DECIMAL(18,2)'))
                        FROM @XML.nodes('Claim/Services/Service') AS T(P)
                        CROSS APPLY P.nodes('ServiceItemSet/ServiceItemSet') AS X(S)

                        
                        -- SUB SERVICES
                        INSERT INTO #tblServiceServices(ServiceCode, SubServiceCode, QtyAsked, PriceAsked)
                        SELECT
                            P.value('(ServiceCode)[1]', 'NVARCHAR(6)'),
                            S.value('(SubServiceCode)[1]', 'NVARCHAR(6)'),
                            CONVERT(INT, S.value('(QtyAsked)[1]', 'INT')),
                            CONVERT(DECIMAL(18,2), S.value('(PriceAsked)[1]', 'DECIMAL(18,2)'))
                        FROM @XML.nodes('Claim/Services/Service') AS T(P)
                        CROSS APPLY P.nodes('ServiceServiceSet/ServiceServiceSet') AS X(S)

                        

                        --isValid HFCode

                        SELECT @HFID = HFID FROM tblHF WHERE HFCode = @HFCode AND ValidityTo IS NULL
                        IF @HFID IS NULL
                            RETURN 1
                            
                        --isDuplicate ClaimCode
                        IF EXISTS(SELECT ClaimCode FROM tblClaim WHERE ClaimCode = @ClaimCode AND HFID = @HFID AND ValidityTo IS NULL)
                            RETURN 2

                        --isValid CHFID
                        SELECT @InsureeID = InsureeID FROM tblInsuree WHERE CHFID = @CHFID AND ValidityTo IS NULL
                        IF @InsureeID IS NULL
                            RETURN 3

                        --isValid EndDate
                        IF DATEDIFF(DD,@ENDDATE,@STARTDATE) > 0
                            RETURN 4
                            
                        --isValid ICDCode
                        SELECT @ICDID = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode AND ValidityTo IS NULL
                        IF @ICDID IS NULL
                            RETURN 5
                        
                        -- isValid Program
                        SELECT @programId = idProgram FROM tblProgram WHERE Name = @Program
                        IF @programId IS NULL
                            RETURN 10
                        
                        IF NOT NULLIF(@ICDCode1, '')IS NULL
                        BEGIN
                            SELECT @ICDID1 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode1 AND ValidityTo IS NULL
                            IF @ICDID1 IS NULL
                                RETURN 5
                        END
                        
                        IF NOT NULLIF(@ICDCode2, '') IS NULL
                        BEGIN
                            SELECT @ICDID2 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode2 AND ValidityTo IS NULL
                            IF @ICDID2 IS NULL
                                RETURN 5
                        END
                        
                        IF NOT NULLIF(@ICDCode3, '') IS NULL
                        BEGIN
                            SELECT @ICDID3 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode3 AND ValidityTo IS NULL
                            IF @ICDID3 IS NULL
                                RETURN 5
                        END
                        
                        IF NOT NULLIF(@ICDCode4, '') IS NULL
                        BEGIN
                            SELECT @ICDID4 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode4 AND ValidityTo IS NULL
                            IF @ICDID4 IS NULL
                                RETURN 5
                        END		
                        --isValid Claimed Amount
                        --THIS CONDITION CAN BE PUT BACK
                        --IF @Total <= 0
                        --	RETURN 6
                            
                        --isValid ItemCode
                        IF EXISTS (SELECT I.ItemCode
                        FROM tblItems I FULL OUTER JOIN #tblItem TI ON I.ItemCode COLLATE DATABASE_DEFAULT = TI.ItemCode COLLATE DATABASE_DEFAULT
                        WHERE I.ItemCode IS NULL AND I.ValidityTo IS NULL)
                            RETURN 7
                            
                        --isValid ServiceCode
                        IF EXISTS(SELECT S.ServCode
                        FROM tblServices S FULL OUTER JOIN #tblService TS ON S.ServCode COLLATE DATABASE_DEFAULT = TS.ServiceCode COLLATE DATABASE_DEFAULT
                        WHERE S.ServCode IS NULL AND S.ValidityTo IS NULL)
                            RETURN 8
                        
                        --isValid Claim Admin
                        IF @isClaimAdminRequired = 1
                            BEGIN	
                                SELECT @ClaimAdminId = ClaimAdminId FROM tblClaimAdmin WHERE ClaimAdminCode = @ClaimAdmin AND ValidityTo IS NULL
                                IF @ClaimAdminId IS NULL
                                    RETURN 9
                            END
                        ELSE
                            IF @isClaimAdminOptional = 1
                                BEGIN	
                                    SELECT @ClaimAdminId = ClaimAdminId FROM tblClaimAdmin WHERE ClaimAdminCode = @ClaimAdmin AND ValidityTo IS NULL
                                END
                        
                        
                        --isValid SubItemCode
                        IF EXISTS (
                            SELECT s.SubItemCode
                            FROM #tblServiceItems s
                            LEFT JOIN tblItems i ON i.ItemCode COLLATE DATABASE_DEFAULT = s.SubItemCode COLLATE DATABASE_DEFAULT
                            WHERE i.ItemCode IS NULL AND i.ValidityTo IS NULL
                        )
                            RETURN 7

                        --isValid SubServiceCode
                        IF EXISTS (
                            SELECT s.SubServiceCode
                            FROM #tblServiceServices s
                            LEFT JOIN tblServices ss ON ss.ServCode COLLATE DATABASE_DEFAULT = s.SubServiceCode COLLATE DATABASE_DEFAULT
                            WHERE ss.ServCode IS NULL AND ss.ValidityTo IS NULL
                        )
                            RETURN 8


                    BEGIN TRAN CLAIM
                        INSERT INTO tblClaim(InsureeID,ClaimCode,DateFrom,DateTo,ICDID,ClaimStatus,Claimed,DateClaimed,Explanation,AuditUserID,HFID,ClaimAdminId,ICDID1,ICDID2,ICDID3,ICDID4,program,VisitType,GuaranteeId,source)
                                    VALUES(@InsureeID,@ClaimCode,@StartDate,@EndDate,@ICDID,2,@Total,@ClaimDate,@Comment,-1,@HFID,@ClaimAdminId,@ICDID1,@ICDID2,@ICDID3,@ICDID4,@programId,@VisitType,@GuaranteeId,'XML');

                        SELECT @ClaimID = SCOPE_IDENTITY();
                        
                        ;WITH PLID AS
                        (
                            SELECT PLID.ItemId, PLID.PriceOverule
                            FROM tblHF HF
                            INNER JOIN tblPLItems PLI ON PLI.PLItemId = HF.PLItemID
                            INNER JOIN tblPLItemsDetail PLID ON PLID.PLItemId = PLI.PLItemId
                            WHERE HF.ValidityTo IS NULL
                            AND PLI.ValidityTo IS NULL
                            AND PLID.ValidityTo IS NULL
                            AND HF.HFID = @HFID
                        )
                        INSERT INTO tblClaimItems(ClaimID,ItemID,QtyProvided,PriceAsked,AuditUserID)
                        SELECT @ClaimID, I.ItemId, T.ItemQuantity, COALESCE(NULLIF(T.ItemPrice,0),PLID.PriceOverule,I.ItemPrice)ItemPrice, -1
                        FROM #tblItem T 
                        INNER JOIN tblItems I  ON T.ItemCode COLLATE DATABASE_DEFAULT = I.ItemCode COLLATE DATABASE_DEFAULT AND I.ValidityTo IS NULL
                        LEFT OUTER JOIN PLID ON PLID.ItemID = I.ItemID
                        
                        
                        SELECT @TotalItems = SUM(PriceAsked * QtyProvided) FROM tblClaimItems 
                                    WHERE ClaimID = @ClaimID
                                    GROUP BY ClaimID

                        ;WITH PLSD AS
                        (
                            SELECT PLSD.ServiceId, PLSD.PriceOverule
                            FROM tblHF HF
                            INNER JOIN tblPLServices PLS ON PLS.PLServiceId = HF.PLServiceID
                            INNER JOIN tblPLServicesDetail PLSD ON PLSD.PLServiceId = PLS.PLServiceId
                            WHERE HF.ValidityTo IS NULL
                            AND PLS.ValidityTo IS NULL
                            AND PLSD.ValidityTo IS NULL
                            AND HF.HFID = @HFID
                        )
                        INSERT INTO tblClaimServices(ClaimId, ServiceID, QtyProvided, PriceAsked, AuditUserID)
                        SELECT @ClaimID, S.ServiceID, T.ServiceQuantity,COALESCE(NULLIF(T.ServicePrice,0),PLSD.PriceOverule,S.ServPrice)ServicePrice , -1
                        FROM #tblService T 
                        INNER JOIN tblServices S ON T.ServiceCode COLLATE DATABASE_DEFAULT = S.ServCode COLLATE DATABASE_DEFAULT AND S.ValidityTo IS NULL
                        LEFT OUTER JOIN PLSD ON PLSD.ServiceId = S.ServiceId
                        
                        
                        -- Insert Service Items
                        INSERT INTO tblClaimServicesItems (qty_provided,qty_displayed,price,ClaimServiceID,ItemID)
                        SELECT s.QtyAsked, s.QtyAsked, s.PriceAsked, cs.ClaimServiceID, i.ItemID
                        FROM #tblServiceItems s
                        JOIN tblClaimServices cs
                            ON cs.ClaimID = @ClaimID
                            AND cs.ServiceID = (
                                SELECT ServiceID FROM tblServices 
                                WHERE ServCode COLLATE DATABASE_DEFAULT = s.ServiceCode COLLATE DATABASE_DEFAULT
                                AND ValidityTo IS NULL
                            )
                        JOIN tblItems i
                            ON i.ItemCode COLLATE DATABASE_DEFAULT = s.SubItemCode COLLATE DATABASE_DEFAULT
                            AND i.ValidityTo IS NULL;

                        
                        -- Insert Service Services
                        INSERT INTO tblClaimServicesService (qty_provided, qty_displayed, price, claimServiceID, ServiceId)
                        SELECT s.QtyAsked, s.QtyAsked, s.PriceAsked, cs.ClaimServiceID, ss.ServiceID
                        FROM #tblServiceServices s
                        JOIN tblClaimServices cs
                            ON cs.ClaimID = @ClaimID
                            AND cs.ServiceID = (
                                SELECT ServiceID FROM tblServices 
                                WHERE ServCode COLLATE DATABASE_DEFAULT = s.ServiceCode COLLATE DATABASE_DEFAULT
                                AND ValidityTo IS NULL
                            )
                        JOIN tblServices ss
                            ON ss.ServCode COLLATE DATABASE_DEFAULT = s.SubServiceCode COLLATE DATABASE_DEFAULT
                            AND ss.ValidityTo IS NULL;
                            
                            
                                    
                                    SELECT @TotalServices = SUM(PriceAsked * QtyProvided) FROM tblClaimServices 
                                    WHERE ClaimID = @ClaimID
                                    GROUP BY ClaimID
                                
                                    UPDATE tblClaim SET Claimed = ISNULL(@TotalItems,0) + ISNULL(@TotalServices,0)
                                    WHERE ClaimID = @ClaimID
                                    
                    COMMIT TRAN CLAIM
                    
                    
                    SELECT @ClaimID  = IDENT_CURRENT('tblClaim')
                    
                    IF @ByPassSubmit = 0
                        EXEC uspSubmitSingleClaim -1, @ClaimID,0 
                    
                END TRY
                BEGIN CATCH
                    IF @@TRANCOUNT > 0
                        ROLLBACK TRAN CLAIM
                        SELECT ERROR_MESSAGE()
                    RETURN -1
                END CATCH
                
                RETURN 0
            END

            """
            if settings.MSSQL else
            """
            CREATE OR REPLACE FUNCTION public."uspUpdateClaimFromPhone"(
                p_xml TEXT,
                p_bypasssubmit BOOLEAN DEFAULT FALSE
            )
            RETURNS INTEGER AS $$
            DECLARE
                v_claimid INTEGER;
                v_claimdate DATE;
                v_hfcode VARCHAR(8);
                v_claimadmin VARCHAR(8);
                v_claimcode VARCHAR(50);
                v_chfid VARCHAR(50);
                v_startdate DATE;
                v_enddate DATE;
                v_icdcode VARCHAR(6);
                v_comment TEXT;
                v_total NUMERIC(18,2);
                v_icdcode1 VARCHAR(6); v_icdcode2 VARCHAR(6); v_icdcode3 VARCHAR(6); v_icdcode4 VARCHAR(6);
                v_visittype CHAR(1);
                v_guaranteeid VARCHAR(50);
                v_program VARCHAR(100);
                v_programid INTEGER;
                v_hfid INTEGER;
                v_claimadminid INTEGER;
                v_insureeid INTEGER;
                v_icdid INTEGER;
                v_icdid1 INTEGER; v_icdid2 INTEGER; v_icdid3 INTEGER; v_icdid4 INTEGER;

                v_totalitems NUMERIC(18,2) := 0;
                v_totalservices NUMERIC(18,2) := 0;

                v_isclaimadminrequired BOOLEAN;
                v_isclaimadminoptional BOOLEAN;

                v_xml XML;
            BEGIN
                v_xml := p_xml::XML;

                SELECT (CASE "Adjustibility" WHEN 'M' THEN TRUE ELSE FALSE END) INTO v_isclaimadminrequired FROM "tblControls" WHERE "FieldName" = 'ClaimAdministrator';
                SELECT (CASE "Adjustibility" WHEN 'O' THEN TRUE ELSE FALSE END) INTO v_isclaimadminoptional FROM "tblControls" WHERE "FieldName" = 'ClaimAdministrator';

                -- EXTRACT DETAILS
                SELECT
                    (xpath('//Details/ClaimDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Details/HFCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/ClaimAdmin/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/ClaimCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/CHFID/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/StartDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Details/EndDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Details/ICDCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/Comment/text()', v_xml))[1]::TEXT,
                    COALESCE(NULLIF((xpath('//Details/Total/text()', v_xml))[1]::TEXT, ''), '0')::NUMERIC,
                    (xpath('//Details/ICDCode1/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/ICDCode2/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/ICDCode3/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/ICDCode4/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/VisitType/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/GuaranteeNumber/text()', v_xml))[1]::TEXT,
                    (xpath('//Details/Program/text()', v_xml))[1]::TEXT
                INTO
                    v_claimdate, v_hfcode, v_claimadmin, v_claimcode, v_chfid,
                    v_startdate, v_enddate, v_icdcode, v_comment, v_total,
                    v_icdcode1, v_icdcode2, v_icdcode3, v_icdcode4,
                    v_visittype, v_guaranteeid, v_program;

                -- VALIDATIONS
                SELECT "HfID" INTO v_hfid FROM "tblHF" WHERE "HFCode" = v_hfcode AND "ValidityTo" IS NULL;
                IF NOT FOUND THEN RETURN 1; END IF;

                IF EXISTS(SELECT 1 FROM "tblClaim" WHERE "ClaimCode" = v_claimcode AND "HFID" = v_hfid AND "ValidityTo" IS NULL) THEN RETURN 2; END IF;

                SELECT "InsureeID" INTO v_insureeid FROM "tblInsuree" WHERE "CHFID" = v_chfid AND "ValidityTo" IS NULL;
                IF NOT FOUND THEN RETURN 3; END IF;

                IF v_enddate < v_startdate THEN RETURN 4; END IF;

                SELECT "ICDID" INTO v_icdid FROM "tblICDCodes" WHERE "ICDCode" = v_icdcode AND "ValidityTo" IS NULL;
                IF NOT FOUND THEN RETURN 5; END IF;

                IF EXISTS (SELECT 1 FROM xmltable('/Claim/Items/Item' PASSING v_xml COLUMNS code TEXT PATH 'ItemCode') xt LEFT JOIN "tblItems" i ON i."ItemCode" = xt.code AND i."ValidityTo" IS NULL WHERE i."ItemID" IS NULL AND xt.code IS NOT NULL) THEN RETURN 7; END IF;
                IF EXISTS (SELECT 1 FROM xmltable('/Claim/Services/Service' PASSING v_xml COLUMNS code TEXT PATH 'ServiceCode') xt LEFT JOIN "tblServices" s ON s."ServCode" = xt.code AND s."ValidityTo" IS NULL WHERE s."ServiceID" IS NULL AND xt.code IS NOT NULL) THEN RETURN 8; END IF;
                
                SELECT "idProgram" INTO v_programid FROM "tblProgram" WHERE "Name" = v_program;
                IF NOT FOUND THEN RETURN 10; END IF;

                IF v_isclaimadminrequired OR v_isclaimadminoptional THEN
                    SELECT "ClaimAdminId" INTO v_claimadminid FROM "tblClaimAdmin" WHERE "ClaimAdminCode" = v_claimadmin AND "ValidityTo" IS NULL;
                    IF v_isclaimadminrequired AND v_claimadminid IS NULL THEN RETURN 9; END IF;
                END IF;

                -- TEMP TABLES
                CREATE TEMP TABLE tmp_items (itemcode TEXT, itemprice NUMERIC, itemquantity NUMERIC) ON COMMIT DROP;
                CREATE TEMP TABLE tmp_services (servicecode TEXT, serviceprice NUMERIC, servicequantity NUMERIC) ON COMMIT DROP;
                CREATE TEMP TABLE tmp_serviceitems (servicecode TEXT, subitemcode TEXT, qtyasked NUMERIC, priceasked NUMERIC) ON COMMIT DROP;
                CREATE TEMP TABLE tmp_serviceservices (servicecode TEXT, subservicecode TEXT, qtyasked NUMERIC, priceasked NUMERIC) ON COMMIT DROP;

                INSERT INTO tmp_items 
                SELECT * FROM xmltable('//Claim/Items/Item' PASSING v_xml COLUMNS code TEXT PATH 'ItemCode', price NUMERIC PATH 'ItemPrice', qty NUMERIC PATH 'ItemQuantity');

                INSERT INTO tmp_services 
                SELECT * FROM xmltable('//Claim/Services/Service' PASSING v_xml COLUMNS code TEXT PATH 'ServiceCode', price NUMERIC PATH 'ServicePrice', qty NUMERIC PATH 'ServiceQuantity');

                -- Extract Service Items
                INSERT INTO tmp_serviceitems (servicecode, subitemcode, qtyasked, priceasked)
                SELECT 
                    xt.servicecode, xt.subitemcode, xt.qtyasked, xt.priceasked
                FROM xmltable(
                    '//Claim/Services/Service/ServiceItemSet/ServiceItemSet' PASSING v_xml
                    COLUMNS 
                        servicecode TEXT PATH './../../ServiceCode',
                        subitemcode TEXT PATH 'SubItemCode',
                        qtyasked NUMERIC PATH 'QtyAsked',
                        priceasked NUMERIC PATH 'PriceAsked'
                ) xt;

                -- Extract Service Services
                INSERT INTO tmp_serviceservices (servicecode, subservicecode, qtyasked, priceasked)
                SELECT 
                    xt.servicecode, xt.subservicecode, xt.qtyasked, xt.priceasked
                FROM xmltable(
                    '//Claim/Services/Service/ServiceServiceSet/ServiceServiceSet' PASSING v_xml
                    COLUMNS 
                        servicecode TEXT PATH './../../ServiceCode',
                        subservicecode TEXT PATH 'SubServiceCode',
                        qtyasked NUMERIC PATH 'QtyAsked',
                        priceasked NUMERIC PATH 'PriceAsked'
                ) xt;

                -- Claim
                INSERT INTO "tblClaim"("InsureeID","ClaimCode","DateFrom","DateTo","ICDID","ClaimStatus","Claimed","DateClaimed","Explanation","AuditUserID","HFID","ClaimAdminId","ICDID1","ICDID2","ICDID3","ICDID4","program","VisitType","GuaranteeId","Feedback","source")
                VALUES (v_insureeid, v_claimcode, v_startdate, v_enddate, v_icdid, 2, v_total, v_claimdate, v_comment, -1, v_hfid, v_claimadminid, v_icdid1, v_icdid2, v_icdid3, v_icdid4, v_programid, v_visittype, v_guaranteeid, FALSE, 'XML')
                RETURNING "ClaimID" INTO v_claimid;

                -- Insert Items
                INSERT INTO "tblClaimItems"("ClaimID","ItemID","QtyProvided","PriceAsked","AuditUserID")
                SELECT v_claimid, i."ItemID", t.itemquantity, COALESCE(NULLIF(t.itemprice,0), plid."PriceOverule", i."ItemPrice"), -1
                FROM tmp_items t 
                JOIN "tblItems" i ON i."ItemCode" = t.itemcode AND i."ValidityTo" IS NULL
                LEFT JOIN (SELECT plid."ItemID", plid."PriceOverule" FROM "tblHF" hf JOIN "tblPLItemsDetail" plid ON plid."PLItemID" = hf."PLItemID" WHERE hf."HfID" = v_hfid AND hf."ValidityTo" IS NULL) plid ON plid."ItemID" = i."ItemID";

                -- Insert Services
                INSERT INTO "tblClaimServices"("ClaimID","ServiceID","QtyProvided","PriceAsked","AuditUserID","ClaimServiceStatus")
                SELECT v_claimid, s."ServiceID", t.servicequantity, COALESCE(NULLIF(t.serviceprice,0), plsd."PriceOverule", s."ServPrice"), -1, 1
                FROM tmp_services t 
                JOIN "tblServices" s ON s."ServCode" = t.servicecode AND s."ValidityTo" IS NULL
                LEFT JOIN (SELECT plsd."ServiceID", plsd."PriceOverule" FROM "tblHF" hf JOIN "tblPLServicesDetail" plsd ON plsd."PLServiceID" = hf."PLServiceID" WHERE hf."HfID" = v_hfid AND hf."ValidityTo" IS NULL) plsd ON plsd."ServiceID" = s."ServiceID";

                -- Insert Service Items
                INSERT INTO "tblClaimServicesItems"("qty_provided","qty_displayed","price","ClaimServiceID","ItemID")
                SELECT si.qtyasked, si.qtyasked, si.priceasked, cs."ClaimServiceID", i."ItemID"
                FROM tmp_serviceitems si
                JOIN "tblServices" s ON s."ServCode" = si.servicecode AND s."ValidityTo" IS NULL
                JOIN "tblClaimServices" cs ON cs."ClaimID" = v_claimid AND cs."ServiceID" = s."ServiceID"
                JOIN "tblItems" i ON i."ItemCode" = si.subitemcode AND i."ValidityTo" IS NULL;

                -- Insert Service Services
                INSERT INTO "tblClaimServicesService"("qty_provided","qty_displayed","price","claimServiceID","ServiceId")
                SELECT ss.qtyasked, ss.qtyasked, ss.priceasked, cs."ClaimServiceID", ssub."ServiceID"
                FROM tmp_serviceservices ss
                JOIN "tblServices" s ON s."ServCode" = ss.servicecode AND s."ValidityTo" IS NULL
                JOIN "tblClaimServices" cs ON cs."ClaimID" = v_claimid AND cs."ServiceID" = s."ServiceID"
                JOIN "tblServices" ssub ON ssub."ServCode" = ss.subservicecode AND ssub."ValidityTo" IS NULL;

                -- UPDATE TOTAL AND SUBMIT
                UPDATE "tblClaim" SET "Claimed" = (SELECT COALESCE(SUM("PriceAsked" * "QtyProvided"), 0) FROM "tblClaimServices" WHERE "ClaimID" = v_claimid) + (SELECT COALESCE(SUM("PriceAsked" * "QtyProvided"), 0) FROM "tblClaimItems" WHERE "ClaimID" = v_claimid) WHERE "ClaimID" = v_claimid;

                IF NOT p_bypasssubmit THEN PERFORM uspsubmitsingleclaim(-1, v_claimid, 0); END IF;

                RETURN 0;
            END;
            $$ LANGUAGE plpgsql;


            """,
        )
    ]
