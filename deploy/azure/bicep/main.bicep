targetScope = 'resourceGroup'

@description('Azure region')
param location string = resourceGroup().location

@description('Name prefix (lowercase alphanumeric)')
@minLength(3)
@maxLength(20)
param namePrefix string = 'gie'

@description('Postgres admin username')
param postgresAdminLogin string = 'gieadmin'

@secure()
@description('Postgres admin password (12+ chars, complexity required)')
param postgresAdminPassword string

@description('AKS node count')
param aksNodeCount int = 3

@description('AKS node VM size')
param aksNodeVmSize string = 'Standard_D4s_v3'

@description('Postgres databases to create on the Flexible Server')
param postgresDatabases array = [
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

var acrName = toLower(replace('${namePrefix}acr${uniqueString(resourceGroup().id)}', '-', ''))
var aksName = '${namePrefix}-aks'
var postgresName = toLower(take('${namePrefix}-pg-${uniqueString(resourceGroup().id)}', 63))

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    name: acrName
    location: location
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    name: postgresName
    location: location
    administratorLogin: postgresAdminLogin
    administratorPassword: postgresAdminPassword
    databases: postgresDatabases
  }
}

module aks 'modules/aks.bicep' = {
  name: 'aks'
  params: {
    name: aksName
    location: location
    dnsPrefix: '${namePrefix}aks'
    nodeCount: aksNodeCount
    nodeVmSize: aksNodeVmSize
    acrName: acr.outputs.name
  }
}

output acrLoginServer string = acr.outputs.loginServer
output acrName string = acr.outputs.name
output aksName string = aks.outputs.name
output aksFqdn string = aks.outputs.fqdn
output postgresFqdn string = postgres.outputs.fqdn
output redisHostName string = 'redis.gie.svc.cluster.local'
output redisSslPort int = 6379
output resourceGroup string = resourceGroup().name
