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
                        INSERT INTO tblClaim(InsureeID,ClaimCode,DateFrom,DateTo,ICDID,ClaimStatus,Claimed,DateClaimed,Explanation,AuditUserID,HFID,ClaimAdminId,ICDID1,ICDID2,ICDID3,ICDID4,program,VisitType,GuaranteeId)
                                    VALUES(@InsureeID,@ClaimCode,@StartDate,@EndDate,@ICDID,2,@Total,@ClaimDate,@Comment,-1,@HFID,@ClaimAdminId,@ICDID1,@ICDID2,@ICDID3,@ICDID4,@programId,@VisitType,@GuaranteeId);

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
                v_icdcode1 VARCHAR(6);
                v_icdcode2 VARCHAR(6);
                v_icdcode3 VARCHAR(6);
                v_icdcode4 VARCHAR(6);
                v_visittype CHAR(1);
                v_guaranteeid VARCHAR(50);
                v_program VARCHAR(100);
                v_programid INTEGER;

                v_hfid INTEGER;
                v_claimadminid INTEGER;
                v_insureeid INTEGER;

                v_icdid INTEGER;
                v_icdid1 INTEGER;
                v_icdid2 INTEGER;
                v_icdid3 INTEGER;
                v_icdid4 INTEGER;

                v_totalitems NUMERIC(18,2) := 0;
                v_totalservices NUMERIC(18,2) := 0;

                v_isclaimadminrequired BOOLEAN;
                v_isclaimadminoptional BOOLEAN;

                v_xml XML;
            BEGIN
                -- Convert XML
                v_xml := p_xml::XML;

                --   EXTRACTION XML
                SELECT
                    (xpath('//Claim/Details/ClaimDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Claim/Details/HFCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/ClaimAdmin/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/ClaimCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/CHFID/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/StartDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Claim/Details/EndDate/text()', v_xml))[1]::TEXT::DATE,
                    (xpath('//Claim/Details/ICDCode/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/Comment/text()', v_xml))[1]::TEXT,
                    COALESCE(NULLIF((xpath('//Claim/Details/Total/text()', v_xml))[1]::TEXT, ''), '0')::NUMERIC,
                    (xpath('//Claim/Details/ICDCode1/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/ICDCode2/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/ICDCode3/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/ICDCode4/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/VisitType/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/GuaranteeNo/text()', v_xml))[1]::TEXT,
                    (xpath('//Claim/Details/Program/text()', v_xml))[1]::TEXT
                INTO
                    v_claimdate, v_hfcode, v_claimadmin, v_claimcode, v_chfid,
                    v_startdate, v_enddate, v_icdcode, v_comment, v_total,
                    v_icdcode1, v_icdcode2, v_icdcode3, v_icdcode4,
                    v_visittype, v_guaranteeid, v_program;

                --   CONTROLES ADMINISTRATIFS

                SELECT
                    CASE WHEN "Adjustibility" = 'M' THEN TRUE ELSE FALSE END,
                    CASE WHEN "Adjustibility" = 'O' THEN TRUE ELSE FALSE END
                INTO v_isclaimadminrequired, v_isclaimadminoptional
                FROM "tblControls"
                WHERE "FieldName" = 'ClaimAdministrator';

                --   VALIDATION HF

                SELECT "HfID"
                INTO v_hfid
                FROM "tblHF"
                WHERE "HFCode" = v_hfcode AND "ValidityTo" IS NULL;

                IF NOT FOUND THEN RETURN 1; END IF;

                --   DUPLICATE CLAIM

                PERFORM 1 FROM "tblClaim"
                WHERE "ClaimCode" = v_claimcode
                AND "HFID" = v_hfid
                AND "ValidityTo" IS NULL;

                IF FOUND THEN RETURN 2; END IF;

                --   INSUREE

                SELECT "InsureeID"
                INTO v_insureeid
                FROM "tblInsuree"
                WHERE "CHFID" = v_chfid AND "ValidityTo" IS NULL;

                IF NOT FOUND THEN RETURN 3; END IF;

                --   DATES

                IF v_enddate < v_startdate THEN RETURN 4; END IF;

                --   ICD CODES

                SELECT "ICDID"
                INTO v_icdid
                FROM "tblICDCodes"
                WHERE "ICDCode" = v_icdcode AND "ValidityTo" IS NULL;

                IF NOT FOUND THEN RETURN 5; END IF;

                -- ICD secondaires

                IF v_icdcode1 IS NOT NULL AND TRIM(v_icdcode1) <> '' THEN
                    SELECT "ICDID" INTO v_icdid1
                    FROM "tblICDCodes"
                    WHERE "ICDCode" = v_icdcode1 AND "ValidityTo" IS NULL;

                    IF NOT FOUND THEN RETURN 5; END IF;
                END IF;

                IF v_icdcode2 IS NOT NULL AND TRIM(v_icdcode2) <> '' THEN
                    SELECT "ICDID" INTO v_icdid2
                    FROM "tblICDCodes"
                    WHERE "ICDCode" = v_icdcode2 AND "ValidityTo" IS NULL;

                    IF NOT FOUND THEN RETURN 5; END IF;
                END IF;

                IF v_icdcode3 IS NOT NULL AND TRIM(v_icdcode3) <> '' THEN
                    SELECT "ICDID" INTO v_icdid3
                    FROM "tblICDCodes"
                    WHERE "ICDCode" = v_icdcode3 AND "ValidityTo" IS NULL;

                    IF NOT FOUND THEN RETURN 5; END IF;
                END IF;

                IF v_icdcode4 IS NOT NULL AND TRIM(v_icdcode4) <> '' THEN
                    SELECT "ICDID" INTO v_icdid4
                    FROM "tblICDCodes"
                    WHERE "ICDCode" = v_icdcode4 AND "ValidityTo" IS NULL;

                    IF NOT FOUND THEN RETURN 5; END IF;
                END IF;

                -- PROGRAMME

                SELECT "idProgram"
                INTO v_programid
                FROM "tblProgram"
                WHERE "Name" = v_program;

                IF NOT FOUND THEN RETURN 10; END IF;

                -- CLAIM ADMIN

                IF v_isclaimadminrequired THEN
                    SELECT "ClaimAdminId"
                    INTO v_claimadminid
                    FROM "tblClaimAdmin"
                    WHERE "ClaimAdminCode" = v_claimadmin AND "ValidityTo" IS NULL;

                    IF NOT FOUND THEN RETURN 9; END IF;
                ELSIF v_isclaimadminoptional THEN
                    SELECT "ClaimAdminId"
                    INTO v_claimadminid
                    FROM "tblClaimAdmin"
                    WHERE "ClaimAdminCode" = v_claimadmin AND "ValidityTo" IS NULL;
                END IF;

                -- CREATION TEMP TABLES

                DROP TABLE IF EXISTS tmp_items;
                CREATE TEMP TABLE tmp_items (
                    itemcode VARCHAR(6),
                    itemprice NUMERIC(18,2),
                    itemquantity NUMERIC(18,2)
                );

                DROP TABLE IF EXISTS tmp_services;
                CREATE TEMP TABLE tmp_services (
                    servicecode VARCHAR(6),
                    serviceprice NUMERIC(18,2),
                    servicequantity NUMERIC(18,2)
                );

                -- INSERT ITEMS

                INSERT INTO tmp_items
                SELECT
                    (xpath('//ItemCode/text()', x))[1]::TEXT,
                    (xpath('//ItemPrice/text()', x))[1]::TEXT::NUMERIC,
                    (xpath('//ItemQuantity/text()', x))[1]::TEXT::NUMERIC
                FROM unnest(xpath('//Claim/Items/Item', v_xml)) AS x;

                -- INSERT SERVICES

                INSERT INTO tmp_services
                SELECT
                    (xpath('//ServiceCode/text()', x))[1]::TEXT,
                    (xpath('//ServicePrice/text()', x))[1]::TEXT::NUMERIC,
                    (xpath('//ServiceQuantity/text()', x))[1]::TEXT::NUMERIC
                FROM unnest(xpath('//Claim/Services/Service', v_xml)) AS x;

                -- VALIDATION ITEMS / SERVICES

                IF EXISTS (
                    SELECT 1 FROM tmp_items ti
                    LEFT JOIN "tblItems" i
                        ON i."ItemCode" = ti.itemcode AND i."ValidityTo" IS NULL
                    WHERE i."ItemID" IS NULL
                ) THEN RETURN 7; END IF;

                IF EXISTS (
                    SELECT 1 FROM tmp_services ts
                    LEFT JOIN "tblServices" s
                        ON s."ServCode" = ts.servicecode AND s."ValidityTo" IS NULL
                    WHERE s."ServiceID" IS NULL
                ) THEN RETURN 8; END IF;

                -- INSERT CLAIM

                INSERT INTO "tblClaim"(
                    "InsureeID","ClaimCode","DateFrom","DateTo","ICDID",
                    "ClaimStatus","Claimed","DateClaimed","Explanation",
                    "AuditUserID","HFID","ClaimAdminId",
                    "ICDID1","ICDID2","ICDID3","ICDID4",
                    "program","VisitType","GuaranteeId"
                )
                VALUES (
                    v_insureeid, v_claimcode, v_startdate, v_enddate, v_icdid,
                    2, v_total, v_claimdate, v_comment,
                    -1, v_hfid, v_claimadminid,
                    v_icdid1, v_icdid2, v_icdid3, v_icdid4,
                    v_programid, v_visittype, v_guaranteeid
                )
                RETURNING "ClaimID" INTO v_claimid;

                -- SUBMIT

                IF NOT p_bypasssubmit THEN
                    PERFORM uspsubmitsingleclaim(-1, v_claimid, 0);
                END IF;

                RETURN 0;

            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Error in uspUpdateClaimFromPhone: %', SQLERRM;
                RETURN -1;
            END;
            $$ LANGUAGE plpgsql;

            """,
        )
    ]
