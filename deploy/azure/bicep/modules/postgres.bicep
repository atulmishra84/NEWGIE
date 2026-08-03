@description('Azure Database for PostgreSQL Flexible Server (Burstable)')
param name string
param location string
param administratorLogin string
@secure()
param administratorPassword string
param skuName string = 'Standard_B1ms'
param storageSizeGB int = 32
param version string = '16'
param databases array = [
  'gie_orchestrator'
  'gie_context'
  'gie_knowledge'
  'gie_policy'
  'gie_risk'
  'gie_compliance'
  'gie_recommendation'
  'gie_policygen'
  'gie_explainability'
  'gie_validation'
  'gie_learning'
  'gie_integration'
]

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: name
  location: location
  sku: {
    name: skuName
    tier: 'Burstable'
  }
  properties: {
    version: version
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource firewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

@batchSize(1)
resource dbs 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = [for db in databases: {
  parent: postgres
  name: db
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}]

output fqdn string = postgres.properties.fullyQualifiedDomainName
output name string = postgres.name
