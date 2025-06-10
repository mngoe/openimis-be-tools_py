from django.db import migrations

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

            """,
        )
    ]
