// Private pipe protocol: credentials never appear in argv or diagnostics.
// This helper ONLY owns the Codex v2 services. It cannot open Claude's item.
#import <Foundation/Foundation.h>
#import <Security/Security.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        BOOL interactive = argc == 2 && strcmp(argv[1], "--interactive") == 0;
        if (argc > 2 || (argc == 2 && !interactive)) return 64;
        SecKeychainSetUserInteractionAllowed(interactive);
        NSData *input = [[NSFileHandle fileHandleWithStandardInput] readDataOfLength:16385];
        if (input.length > 16384) return 64;
        id request = [NSJSONSerialization JSONObjectWithData:input options:0 error:nil];
        if (![request isKindOfClass:[NSDictionary class]]) return 64;
        NSString *service = request[@"service"], *account = request[@"account"];
        NSString *operation = request[@"operation"], *value = request[@"value"];
        NSSet *services = [NSSet setWithArray:@[@"ai.sponge-theory.spongram.codex.v2",
            @"ai.sponge-theory.rayonne.codex.v2", @"ai.sponge-theory.spt-models.codex.v2"]];
        if (![service isKindOfClass:[NSString class]] || ![services containsObject:service]
            || ![account isKindOfClass:[NSString class]] || account.length == 0
            || account.length > 128 || ![operation isKindOfClass:[NSString class]]) return 64;
        NSMutableDictionary *query = [@{(__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
            (__bridge id)kSecAttrService:service, (__bridge id)kSecAttrAccount:account} mutableCopy];
        OSStatus status;
        NSMutableDictionary *reply = [NSMutableDictionary dictionary];
        if ([operation isEqualToString:@"read"]) {
            query[(__bridge id)kSecReturnData] = @YES;
            query[(__bridge id)kSecMatchLimit] = (__bridge id)kSecMatchLimitOne;
            CFTypeRef result = NULL;
            status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &result);
            if (status == errSecSuccess && result) {
                NSData *data = CFBridgingRelease(result);
                NSString *secret = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
                if (!secret) return 65;
                reply[@"value"] = secret;
            }
        } else if ([operation isEqualToString:@"write"]) {
            if (![value isKindOfClass:[NSString class]] || value.length == 0 || value.length > 8192) return 64;
            NSData *data = [value dataUsingEncoding:NSUTF8StringEncoding];
            status = SecItemUpdate((__bridge CFDictionaryRef)query,
                (__bridge CFDictionaryRef)@{(__bridge id)kSecValueData:data});
            if (status == errSecItemNotFound) {
                query[(__bridge id)kSecValueData] = data;
                status = SecItemAdd((__bridge CFDictionaryRef)query, NULL);
            }
        } else if ([operation isEqualToString:@"delete"]) {
            status = SecItemDelete((__bridge CFDictionaryRef)query);
        } else return 64;
        reply[@"status"] = @(status);
        NSData *output = [NSJSONSerialization dataWithJSONObject:reply options:0 error:nil];
        [[NSFileHandle fileHandleWithStandardOutput] writeData:output];
        return 0;
    }
}
